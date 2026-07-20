"""vnstock production data-provider adapter (Vietnam market).

Adapter ONLY — it maps the `vnstock` library's output to the Athena
provider DTOs (`providers.sdk.models`) and implements the SDK ports. It
contains NO business logic (ADR-0003/0017): the decision kernel, risk,
portfolio and behaviour packages never import it.

Design (mirrors the Alpha Vantage adapter):
  - The `vnstock` library sits behind an injectable `VnstockClient`
    Protocol — the only network seam — so the adapter is fully unit- and
    integration-testable with recorded responses and never needs the
    network in CI. Production uses `RealVnstockClient`, which imports
    `vnstock` lazily (so importing this module costs nothing until a VN
    sync actually runs) and normalises every DataFrame to plain records.
  - Resilience (retry/backoff, rate limit, TTL cache, health) is composed
    from the existing Module-2 stack via the `create_vnstock_*` factories —
    this adapter does not re-implement it (requirements 4 & 5).
  - All numeric values become `Decimal` (constitution: never float).
  - Storage into the Data Pipeline is done by passing these providers to
    `ProviderSyncService` (requirement 6) — no new storage path.

Capabilities implemented:
  - Historical OHLCV .............. PriceProvider.daily_bars  (also VNINDEX/VN30)
  - Financial Statements .......... FundamentalProvider.fundamentals
  - Industry Classification ....... SectorProvider.classification
  - Symbol List ................... SymbolListProvider.symbols
  - Company Profile ............... CompanyProfileProvider.profile
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Protocol

from providers.connectors.resilience import (
    HealthMonitor,
    RetryPolicy,
    TokenBucketRateLimiter,
    TtlCache,
)
from providers.connectors.resilient import (
    ResilientFundamentalProvider,
    ResilientPriceProvider,
    ResilientSectorProvider,
)
from providers.connectors.vnstock_source import DEFAULT_SOURCE, resolve_source
from providers.sdk.models import (
    CompanyProfile,
    FundamentalRecord,
    PriceBar,
    SectorMapping,
    SymbolInfo,
)
from shared_kernel.exceptions import DomainError

# vnstock free VCI/TCBS sources: be a courteous client. One request/second
# with a small burst, cached for an hour, is plenty for daily ingestion.
DEFAULT_RATE_PER_SECOND = 1.0
DEFAULT_BURST = 5.0
DEFAULT_CACHE_TTL = 3600.0
# DEFAULT_SOURCE is imported from `vnstock_source` (single source of truth for
# the source name); re-exported here for backward compatibility with callers.

# Index symbols vnstock understands (requirement: VNINDEX, VN30).
INDEX_SYMBOLS = ("VNINDEX", "VN30", "HNXINDEX", "HNX30", "UPCOMINDEX")

Record = dict[str, object]


class VnstockError(DomainError):
    """vnstock returned an error or unusable/empty data."""


# ---------------------------------------------------------------------------
# Network seam
# ---------------------------------------------------------------------------
class VnstockClient(Protocol):
    """The only network seam; production uses `RealVnstockClient`.

    Every method returns plain records (``list[dict]``) — pandas stays
    inside the real client, so the adapter and its tests never depend on
    it. Methods raise `VnstockError` on any upstream failure.
    """

    def history(self, symbol: str, start: str, end: str, interval: str) -> list[Record]: ...

    def all_symbols(self) -> list[Record]: ...

    def industries(self) -> list[Record]: ...

    def company_overview(self, symbol: str) -> list[Record]: ...

    def financial_ratios(self, symbol: str, period: str) -> list[Record]: ...


class RealVnstockClient:
    """Production client backed by the official `vnstock` library.

    `vnstock` is imported lazily and a fresh `Vnstock().stock(...)` handle
    is built per call; every DataFrame is flattened to plain records so no
    pandas types cross the seam. All library exceptions become
    `VnstockError` so the resilience layer can retry/record them.
    """

    def __init__(self, source: str = DEFAULT_SOURCE) -> None:
        # Validate/normalise here too, so a directly constructed client cannot
        # carry an unsupported source silently (no failover; fail loudly).
        self._source = resolve_source(source)

    @property
    def source(self) -> str:
        return self._source

    # -- helpers ------------------------------------------------------------
    @staticmethod
    def _records(frame: object) -> list[Record]:
        """Normalise a pandas DataFrame (possibly MultiIndex) to records."""
        if frame is None:
            return []
        # Flatten MultiIndex columns to single "a_b" strings, then to dicts.
        # `frame` is a pandas DataFrame at runtime; keep it Any so mypy does
        # not fail on the untyped vnstock/pandas surface behind this seam.
        df: object = frame
        try:
            columns = list(df.columns)  # type: ignore[attr-defined]
        except AttributeError as error:  # not a DataFrame
            raise VnstockError(f"vnstock returned a non-tabular result: {type(frame)}") from error
        if columns and isinstance(columns[0], tuple):
            flat = ["_".join(str(p) for p in col if str(p) != "").strip("_") for col in columns]
            df = df.copy()  # type: ignore[attr-defined]
            df.columns = flat  # type: ignore[attr-defined]
        return list(df.to_dict(orient="records"))  # type: ignore[attr-defined]

    def _stock(self, symbol: str):  # type: ignore[no-untyped-def]
        from vnstock import Vnstock  # lazy: no cost until a sync runs

        return Vnstock().stock(symbol=symbol, source=self._source)

    # -- seam methods -------------------------------------------------------
    def history(self, symbol: str, start: str, end: str, interval: str) -> list[Record]:
        try:
            frame = self._stock(symbol).quote.history(start=start, end=end, interval=interval)
        except Exception as error:  # noqa: BLE001 — normalise every upstream failure
            raise VnstockError(
                f"vnstock[{self._source}] history failed for {symbol}: {error}"
            ) from error
        return self._records(frame)

    def all_symbols(self) -> list[Record]:
        try:
            frame = self._stock("VNINDEX").listing.all_symbols()
        except Exception as error:  # noqa: BLE001
            raise VnstockError(f"vnstock[{self._source}] all_symbols failed: {error}") from error
        return self._records(frame)

    def industries(self) -> list[Record]:
        try:
            frame = self._stock("VNINDEX").listing.symbols_by_industries()
        except Exception as error:  # noqa: BLE001
            raise VnstockError(
                f"vnstock[{self._source}] symbols_by_industries failed: {error}"
            ) from error
        return self._records(frame)

    def company_overview(self, symbol: str) -> list[Record]:
        try:
            frame = self._stock(symbol).company.overview()
        except Exception as error:  # noqa: BLE001
            raise VnstockError(
                f"vnstock[{self._source}] company overview failed for {symbol}: {error}"
            ) from error
        return self._records(frame)

    def financial_ratios(self, symbol: str, period: str) -> list[Record]:
        try:
            frame = self._stock(symbol).finance.ratio(period=period, lang="en", dropna=True)
        except Exception as error:  # noqa: BLE001
            raise VnstockError(
                f"vnstock[{self._source}] finance ratio failed for {symbol}: {error}"
            ) from error
        return self._records(frame)


# ---------------------------------------------------------------------------
# Parsing helpers (tolerant to vnstock column-name variation across versions)
# ---------------------------------------------------------------------------
def _first(row: Record, *names: str) -> object | None:
    for name in names:
        if name in row and row[name] is not None:
            return row[name]
    return None


def _decimal(value: object, field: str) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as error:
        raise VnstockError(f"unparseable {field}: {value!r}") from error


def _opt_decimal(value: object) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _to_iso_day(value: object) -> date | None:
    text = str(value)
    # vnstock 'time' is 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM:SS'
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _str(value: object | None) -> str:
    return "" if value is None else str(value)


# A curated allowlist mapping canonical Athena metric names to the vnstock
# ratio column aliases we recognise. Unknown columns are ignored so a
# vendor schema change never crashes ingestion (it just narrows coverage).
_RATIO_METRICS: dict[str, tuple[str, ...]] = {
    "roe": ("roe", "ROE", "roe_percent", "Meta_roe"),
    "roa": ("roa", "ROA", "roa_percent"),
    "pe": ("pe", "PE", "price_to_earning", "priceToEarning"),
    "pb": ("pb", "PB", "price_to_book", "priceToBook"),
    "eps": ("eps", "EPS", "earning_per_share", "earningPerShare"),
    "bvps": ("bvps", "BVPS", "book_value_per_share", "bookValuePerShare"),
    "gross_margin": ("gross_margin", "grossProfitMargin", "gross_profit_margin"),
    "net_margin": ("net_margin", "netProfitMargin", "post_tax_margin"),
    "debt_to_equity": ("debt_to_equity", "debtOnEquity", "de"),
    "current_ratio": ("current_ratio", "currentPayment", "currentRatio"),
    "revenue": ("revenue", "revenue_bn", "net_revenue"),
    "net_income": ("net_income", "post_tax_profit", "profit_after_tax"),
}


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class VnstockProvider:
    """Raw vnstock adapter (no resilience). Implements the VN capabilities.

    Implements: PriceProvider, FundamentalProvider, SectorProvider,
    SymbolListProvider, CompanyProfileProvider.
    """

    client: VnstockClient

    # -- PriceProvider (Historical OHLCV; also VNINDEX/VN30) ----------------
    def daily_bars(self, ticker: str, start: date, end: date) -> tuple[PriceBar, ...]:
        rows = self.client.history(ticker, start.isoformat(), end.isoformat(), "1D")
        bars: list[PriceBar] = []
        for row in rows:
            day = _to_iso_day(_first(row, "time", "date", "tradingDate"))
            if day is None or not (start <= day <= end):
                continue
            close = _opt_decimal(_first(row, "close", "closePrice"))
            if close is None or close <= 0:
                continue  # index/price rows without a valid close are unusable
            bars.append(
                PriceBar(
                    ticker=ticker.upper(),
                    day=day,
                    close=close,
                    open=_opt_decimal(_first(row, "open", "openPrice")),
                    high=_opt_decimal(_first(row, "high", "highPrice")),
                    low=_opt_decimal(_first(row, "low", "lowPrice")),
                    volume=_opt_decimal(_first(row, "volume", "nmVolume", "totalVolume")),
                )
            )
        return tuple(sorted(bars, key=lambda b: b.day))

    # -- FundamentalProvider (Financial Statements / ratios) ----------------
    def fundamentals(self, ticker: str, as_of: date) -> tuple[FundamentalRecord, ...]:
        rows = self.client.financial_ratios(ticker, "year")
        records: list[FundamentalRecord] = []
        for row in rows:
            year = _first(row, "year", "yearReport", "period", "Meta_yearReport")
            if year is None:
                continue
            period = f"{str(year).split('.')[0]}FY"
            for metric, aliases in _RATIO_METRICS.items():
                value = _opt_decimal(_first(row, *aliases))
                if value is not None:
                    records.append(
                        FundamentalRecord(
                            ticker=ticker.upper(), period=period, metric=metric, value=value
                        )
                    )
        return tuple(records)

    # -- SectorProvider (Industry Classification) ---------------------------
    def classification(self, ticker: str) -> SectorMapping | None:
        target = ticker.upper()
        for row in self.client.industries():
            symbol = _str(_first(row, "symbol", "ticker")).upper()
            if symbol != target:
                continue
            sector = _str(_first(row, "icb_name2", "icb_name3", "sector", "industry"))
            industry = _str(_first(row, "icb_name4", "icb_name3", "industry", "sector"))
            exchange = _str(_first(row, "exchange", "comGroupCode", "group_code"))
            return SectorMapping(ticker=target, sector=sector, industry=industry, exchange=exchange)
        return None

    # -- SymbolListProvider (Symbol List) -----------------------------------
    def symbols(self) -> tuple[SymbolInfo, ...]:
        out: list[SymbolInfo] = []
        for row in self.client.all_symbols():
            ticker = _str(_first(row, "ticker", "symbol")).upper()
            if not ticker:
                continue
            out.append(
                SymbolInfo(
                    ticker=ticker,
                    name=_str(_first(row, "organ_name", "organName", "name")),
                    exchange=_str(_first(row, "exchange", "comGroupCode", "group_code")),
                )
            )
        return tuple(out)

    # -- CompanyProfileProvider (Company Profile) ---------------------------
    def profile(self, ticker: str) -> CompanyProfile | None:
        rows = self.client.company_overview(ticker)
        if not rows:
            return None
        row = rows[0]
        return CompanyProfile(
            ticker=ticker.upper(),
            name=_str(_first(row, "organ_name", "organName", "short_name", "company_name")),
            exchange=_str(_first(row, "exchange", "comGroupCode", "group_code")),
            industry=_str(_first(row, "icb_name4", "icb_name3", "industry")),
            sector=_str(_first(row, "icb_name2", "icb_name3", "sector")),
            profile=_str(_first(row, "company_profile", "history", "business_summary")),
            website=_str(_first(row, "website", "web")),
        )


# ---------------------------------------------------------------------------
# Resilient factories (retry/backoff + rate limit + TTL cache + health)
# ---------------------------------------------------------------------------
def _limiter() -> TokenBucketRateLimiter:
    return TokenBucketRateLimiter(rate_per_second=DEFAULT_RATE_PER_SECOND, capacity=DEFAULT_BURST)


def _client(client: VnstockClient | None) -> VnstockClient:
    # Route to the configured source (VNSTOCK_SOURCE); resolve_source validates
    # it and raises a clear error for an unsupported value (no failover).
    return client or RealVnstockClient(source=resolve_source(os.environ.get("VNSTOCK_SOURCE")))


def create_vnstock_price_provider(*, client: VnstockClient | None = None) -> ResilientPriceProvider:
    """Production-ready resilient price provider (OHLCV, incl. VNINDEX/VN30)."""
    return ResilientPriceProvider(
        inner=VnstockProvider(client=_client(client)),
        retry=RetryPolicy(max_attempts=4, base_delay_seconds=1.0),
        limiter=_limiter(),
        cache=TtlCache(ttl_seconds=DEFAULT_CACHE_TTL),
        health=HealthMonitor(name="vnstock-price"),
    )


def create_vnstock_fundamental_provider(
    *, client: VnstockClient | None = None
) -> ResilientFundamentalProvider:
    return ResilientFundamentalProvider(
        inner=VnstockProvider(client=_client(client)),
        retry=RetryPolicy(max_attempts=4, base_delay_seconds=1.0),
        limiter=_limiter(),
        cache=TtlCache(ttl_seconds=DEFAULT_CACHE_TTL),
        health=HealthMonitor(name="vnstock-fundamental"),
    )


def create_vnstock_sector_provider(
    *, client: VnstockClient | None = None
) -> ResilientSectorProvider:
    return ResilientSectorProvider(
        inner=VnstockProvider(client=_client(client)),
        retry=RetryPolicy(max_attempts=4, base_delay_seconds=1.0),
        limiter=_limiter(),
        cache=TtlCache(ttl_seconds=DEFAULT_CACHE_TTL),
        health=HealthMonitor(name="vnstock-sector"),
    )


def create_vnstock_provider(*, client: VnstockClient | None = None) -> VnstockProvider:
    """Raw provider for the non-resilient capabilities (symbol list, profile)."""
    return VnstockProvider(client=_client(client))
