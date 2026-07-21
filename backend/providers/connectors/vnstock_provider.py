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

import logging
import os
import re
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

_LOG = logging.getLogger("athena.providers.vnstock")

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
            # dropna=False: a wide ratio table almost always has a NaN somewhere
            # in each yearly row, and dropna=True drops those rows — which for
            # VCI empties the whole frame (the "0 ratio records" symptom). We
            # tolerate NaNs downstream (`_opt_decimal` returns None), so keep
            # every row and let per-metric parsing decide.
            frame = self._stock(symbol).finance.ratio(period=period, lang="en", dropna=False)
        except Exception as error:  # noqa: BLE001
            raise VnstockError(
                f"vnstock[{self._source}] finance ratio failed for {symbol}: {error}"
            ) from error
        # Log the raw schema (shape + column headers) once per call so a
        # shell-less operator sees exactly what the vendor returned — a 0-row
        # frame still carries its columns, which tells apart "no data" from
        # "columns our parser didn't recognise". INFO, one line per company.
        try:
            _LOG.info(
                "vnstock[%s] finance.ratio %s shape=%s columns=%s",
                self._source,
                symbol.upper(),
                getattr(frame, "shape", None),
                [str(c) for c in list(getattr(frame, "columns", []))[:40]],
            )
        except Exception:  # noqa: BLE001 — diagnostics must never break ingestion
            pass
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


# Canonical metric → the set of *normalised* column tokens we accept for it.
# Normalisation (`_canon`) drops parenthetical units and all non-alphanumerics
# and lowercases, so a vnstock MultiIndex column like ``Profitability_ROE (%)``,
# a flat ``roe``, ``P/E``, ``EPS (VND)`` or ``Debt/Equity`` all collapse to a
# stable token (``roe``, ``pe``, ``eps``, ``debtequity``). Matching on the
# normalised *leaf* name (the part after the MultiIndex group prefix) makes
# ingestion robust to the group headers and unit suffixes VCI/TCBS attach,
# instead of the exact-string matching that silently extracted zero rows.
_RATIO_CANON: dict[str, frozenset[str]] = {
    "roe": frozenset({"roe"}),
    "roa": frozenset({"roa"}),
    "pe": frozenset({"pe", "pricetoearning"}),
    "pb": frozenset({"pb", "pricetobook"}),
    "eps": frozenset({"eps", "earningpershare"}),
    "bvps": frozenset({"bvps", "bookvaluepershare"}),
    "gross_margin": frozenset({"grossprofitmargin", "grossmargin"}),
    "net_margin": frozenset({"netprofitmargin", "netmargin", "posttaxmargin"}),
    "debt_to_equity": frozenset({"debtequity", "debtonequity", "debttoequity"}),
    "current_ratio": frozenset({"currentratio"}),
    "revenue": frozenset({"revenue", "netrevenue", "sales"}),
    "net_income": frozenset({"netincome", "posttaxprofit", "profitaftertax"}),
}
# Inverted: normalised token → canonical metric (first metric that claims it).
_CANON_TO_METRIC: dict[str, str] = {
    token: metric for metric, tokens in _RATIO_CANON.items() for token in tokens
}
# Normalised tokens that identify the reporting-year column.
_YEAR_CANON: frozenset[str] = frozenset({"year", "yearreport", "reportyear", "nam", "period"})


def _canon(value: object) -> str:
    """Normalise a column name to a comparable token (drop units + punctuation).

    ``ROE (%)`` → ``roe``; ``P/E`` → ``pe``; ``EPS (VND)`` → ``eps``;
    ``Debt/Equity`` → ``debtequity``.
    """
    text = re.sub(r"\(.*?\)", "", str(value))  # strip parenthetical units
    return re.sub(r"[^a-z0-9]", "", text.lower())


def _leaf_canon(key: object) -> str:
    """Canonical token for a (possibly MultiIndex-flattened ``group_leaf``) key."""
    return _canon(str(key).split("_")[-1])


def _row_year(row: Record) -> object | None:
    """Find the reporting-year value in a ratio row, tolerant to column naming."""
    for key, value in row.items():
        if value is not None and _leaf_canon(key) in _YEAR_CANON:
            return value
    return None


# The VCI/TCBS ratio frame is *long/transposed*: one row per metric, one column
# per reporting year (headers 'item', 'item_en', 'item_id', '2018', '2019', …).
# These helpers detect that layout and map each metric row to a canonical name.
_YEAR_RE = re.compile(r"^(19|20)\d{2}$")
_LABEL_FIELDS = ("item_id", "item_en", "item")  # machine key first, then labels


def _year_columns(row: Record) -> list[str]:
    """Column keys that name a reporting year (e.g. '2018'…'2025'), sorted desc."""
    return sorted((str(k) for k in row if _YEAR_RE.match(str(k))), reverse=True)


def _metric_from_labels(row: Record) -> str | None:
    """Canonical metric for a long-form row via its item_id / item_en / item."""
    for field in _LABEL_FIELDS:
        metric = _CANON_TO_METRIC.get(_canon(row.get(field)))
        if metric is not None:
            return metric
    return None


def _parse_long_ratios(
    ticker: str, rows: list[Record], year_cols: list[str]
) -> list[FundamentalRecord]:
    """Long/transposed frame: row = metric, columns = years → one record each."""
    records: list[FundamentalRecord] = []
    for row in rows:
        metric = _metric_from_labels(row)
        if metric is None:
            continue
        for year in year_cols:
            value = _opt_decimal(row.get(year))
            if value is not None:
                records.append(
                    FundamentalRecord(ticker=ticker, period=f"{year}FY", metric=metric, value=value)
                )
    return records


def _parse_wide_ratios(ticker: str, rows: list[Record]) -> list[FundamentalRecord]:
    """Wide frame: row = period, columns = metrics (legacy / test shape)."""
    records: list[FundamentalRecord] = []
    for row in rows:
        year = _row_year(row)
        if year is None:
            continue
        period = f"{str(year).split('.')[0]}FY"
        claimed: dict[str, Decimal] = {}  # metric → first non-null value
        for key, raw in row.items():
            metric = _CANON_TO_METRIC.get(_leaf_canon(key))
            if metric is None or metric in claimed:
                continue
            value = _opt_decimal(raw)
            if value is not None:
                claimed[metric] = value
        for metric, value in claimed.items():
            records.append(
                FundamentalRecord(ticker=ticker, period=period, metric=metric, value=value)
            )
    return records


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
        if not rows:
            # The frame came back empty (no exception) — distinguish this from a
            # column mismatch so a shell-less operator sees which one it is.
            _LOG.warning(
                "vnstock[%s] finance.ratio returned 0 rows for %s (empty frame)",
                getattr(self.client, "source", "?"),
                ticker.upper(),
            )
            return ()
        # Two shapes exist across sources: VCI/TCBS return a *long* frame (one
        # row per metric, one column per year); the legacy/AlphaVantage-style
        # shape is *wide* (one row per period, one column per metric). Detect
        # year columns on the first row to pick the parser.
        year_cols = _year_columns(rows[0])
        upper = ticker.upper()
        records = (
            _parse_long_ratios(upper, rows, year_cols)
            if year_cols
            else _parse_wide_ratios(upper, rows)
        )
        if not records:
            # Data came back but nothing matched — surface the metric labels /
            # columns so a shell-less operator sees the exact vendor vocabulary
            # instead of a silent empty result.
            if year_cols:
                labels = sorted(
                    {str(r.get("item_id") or r.get("item_en") or r.get("item")) for r in rows}
                )
                _LOG.warning(
                    "vnstock[%s] fundamentals matched 0 metrics for %s (long form, %d rows); "
                    "year_cols=%s metric_ids=%s",
                    getattr(self.client, "source", "?"),
                    upper,
                    len(rows),
                    year_cols,
                    labels[:60],
                )
            else:
                sample = rows[0]
                _LOG.warning(
                    "vnstock[%s] fundamentals matched 0 metrics for %s (wide form, %d rows); "
                    "columns=%s sample=%s",
                    getattr(self.client, "source", "?"),
                    upper,
                    len(rows),
                    list(sample.keys()),
                    {k: sample[k] for k in list(sample)[:20]},
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
