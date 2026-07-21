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

    def income_statement(self, symbol: str, period: str) -> list[Record]: ...

    def balance_sheet(self, symbol: str, period: str) -> list[Record]: ...


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
            names = ["_".join(str(p) for p in col if str(p) != "").strip("_") for col in columns]
        else:
            names = [str(c) for c in columns]
        # De-duplicate repeated labels (VCI's transposed ratio frame ships many
        # columns with the same year header) so `to_dict` keeps every column's
        # values instead of collapsing duplicates to a single key.
        if len(set(names)) != len(names):
            counts: dict[str, int] = {}
            unique: list[str] = []
            for name in names:
                if name in counts:
                    counts[name] += 1
                    unique.append(f"{name}.{counts[name]}")
                else:
                    counts[name] = 0
                    unique.append(name)
            names = unique
        df = df.copy()  # type: ignore[attr-defined]
        df.columns = names  # type: ignore[attr-defined]
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

    def _log_schema(self, kind: str, symbol: str, frame: object) -> None:
        # Log the raw schema (shape + column headers) once per call so a
        # shell-less operator sees exactly what the vendor returned — a 0-row
        # frame still carries its columns, which tells apart "no data" from
        # "columns our parser didn't recognise". INFO, one line per company.
        try:
            _LOG.info(
                "vnstock[%s] %s %s shape=%s columns=%s",
                self._source,
                kind,
                symbol.upper(),
                getattr(frame, "shape", None),
                [str(c) for c in list(getattr(frame, "columns", []))[:40]],
            )
        except Exception:  # noqa: BLE001 — diagnostics must never break ingestion
            pass

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
        self._log_schema("finance.ratio", symbol, frame)
        return self._records(frame)

    def income_statement(self, symbol: str, period: str) -> list[Record]:
        try:
            frame = self._stock(symbol).finance.income_statement(
                period=period, lang="en", dropna=False
            )
        except Exception as error:  # noqa: BLE001
            raise VnstockError(
                f"vnstock[{self._source}] income_statement failed for {symbol}: {error}"
            ) from error
        self._log_schema("finance.income_statement", symbol, frame)
        return self._records(frame)

    def balance_sheet(self, symbol: str, period: str) -> list[Record]:
        try:
            frame = self._stock(symbol).finance.balance_sheet(
                period=period, lang="en", dropna=False
            )
        except Exception as error:  # noqa: BLE001
            raise VnstockError(
                f"vnstock[{self._source}] balance_sheet failed for {symbol}: {error}"
            ) from error
        self._log_schema("finance.balance_sheet", symbol, frame)
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
    # VCI reports EPS directly in the income statement as 'eps_basic_vnd'
    # (basic EPS, VND) — preferred; diluted stays unmapped to avoid two rows
    # claiming the same metric for a period.
    "eps": frozenset(
        {"eps", "epsvnd", "epsbasicvnd", "basiceps", "earningpershare", "earningspershare"}
    ),
    "bvps": frozenset(
        {"bvps", "bvpsvnd", "bookvaluepershare", "bookvaluepersharevnd", "bookvalpershare"}
    ),
    "gross_margin": frozenset({"grossprofitmargin", "grossmargin"}),
    "net_margin": frozenset({"netprofitmargin", "netmargin", "posttaxmargin", "netprofitmargintt"}),
    "debt_to_equity": frozenset({"debtequity", "debtonequity", "debttoequity"}),
    "current_ratio": frozenset({"currentratio"}),
    "revenue": frozenset(
        {"revenue", "netrevenue", "sales", "netsale", "netsales", "totalrevenue", "salesrevenue"}
    ),
    "net_income": frozenset(
        {
            "netincome",
            "posttaxprofit",
            "profitaftertax",
            "netprofit",
            "netprofitfortheyear",
            "attributabletoparentcompany",
            "profitfortheyear",
        }
    ),
    "ev_ebitda": frozenset({"evebitda", "evtoebitda"}),
    # Book-value inputs — VCI has no direct BVPS, so we capture owners' equity
    # (balance sheet, VND) and shares outstanding (ratio feed, count) and derive
    # BVPS = owners_equity ÷ shares downstream.
    "owners_equity": frozenset({"ownersequity", "ownerequity", "equityattributabletoowners"}),
    "shares": frozenset({"outstandingshares", "sharesoutstanding"}),
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
_LABEL_KEYS = frozenset(_LABEL_FIELDS)


def _metric_from_labels(row: Record) -> str | None:
    """Canonical metric for a long-form row via its item_id / item_en / item."""
    for field in _LABEL_FIELDS:
        metric = _CANON_TO_METRIC.get(_canon(row.get(field)))
        if metric is not None:
            return metric
    return None


def _year_map(rows: list[Record]) -> dict[str, str]:
    """Map each data-column key → reporting year for a transposed frame.

    Two vendor shapes exist:

    * The ratio frame ships its year columns all labelled the same (e.g. sixteen
      columns literally named '2018'), which a dict collapses to one — losing
      every year but one. It carries a 'year' *row* whose values hold the real
      year under each (de-duplicated) column, so we key periods off that row.
    * The income statement / balance sheet name their columns by year directly
      ('2025','2024',…) and carry no 'year' row, so the headers *are* the years.

    Prefer the 'year' row when present (ratio); otherwise use the year headers.
    """
    for row in rows:
        if any(_canon(row.get(field)) in _YEAR_CANON for field in _LABEL_FIELDS):
            mapping: dict[str, str] = {}
            for key, value in row.items():
                if key in _LABEL_KEYS:
                    continue
                year = str(value).split(".")[0]
                if _YEAR_RE.match(year):
                    mapping[str(key)] = year
            if mapping:
                return mapping
    # No 'year' row — the columns are themselves years (income / balance sheet).
    return {str(key): str(key) for key in rows[0] if _YEAR_RE.match(str(key))}


def _parse_long_ratios(
    ticker: str, rows: list[Record], year_map: dict[str, str]
) -> list[FundamentalRecord]:
    """Long/transposed frame: row = metric, columns = years → one record each.

    ``year_map`` is column-key → reporting year (from `_year_map`), so we read
    every year even when the vendor duplicates the column headers.
    """
    records: list[FundamentalRecord] = []
    for row in rows:
        metric = _metric_from_labels(row)
        if metric is None:
            continue
        for key, year in year_map.items():
            value = _opt_decimal(row.get(key))
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
        """Ratios + income statement + balance sheet, merged into one record set.

        The ratio feed carries the valuation/profitability ratios; revenue and
        EPS live in the income statement, and book value in the balance sheet —
        so we pull all three official datasets and canonically map each. The
        two statements are additive and best-effort: if one is unavailable the
        ratios still persist.
        """
        upper = ticker.upper()
        records = list(
            self._parse_dataset(upper, self.client.financial_ratios(upper, "year"), "ratio")
        )
        for dataset in ("income_statement", "balance_sheet"):
            fetch = getattr(self.client, dataset, None)
            if fetch is None:
                continue
            try:
                rows = fetch(upper, "year")
            except Exception as error:  # noqa: BLE001 — statements are additive
                _LOG.warning(
                    "vnstock[%s] %s failed for %s: %s: %s",
                    getattr(self.client, "source", "?"),
                    dataset,
                    upper,
                    type(error).__name__,
                    error,
                )
                continue
            records.extend(self._parse_dataset(upper, rows, dataset))
        return tuple(records)

    def _parse_dataset(
        self, upper: str, rows: list[Record], dataset: str
    ) -> list[FundamentalRecord]:
        """Parse one vnstock financial dataset (long or wide) into records.

        Emits a coverage line (matched metrics + the vendor's full item_id
        vocabulary) on success, and a distinct 0-row / 0-match warning
        otherwise, each tagged with `dataset` so a shell-less operator can see
        exactly what ratio vs income_statement vs balance_sheet returned and
        why a field is empty.
        """
        source = getattr(self.client, "source", "?")
        if not rows:
            _LOG.warning(
                "vnstock[%s] %s returned 0 rows for %s (empty frame)", source, dataset, upper
            )
            return []
        # Long form (VCI/TCBS): row = metric, column = year, identified by a
        # 'year' row. Wide form (legacy/AlphaVantage): row = period.
        year_map = _year_map(rows)
        records = (
            _parse_long_ratios(upper, rows, year_map)
            if year_map
            else _parse_wide_ratios(upper, rows)
        )
        if year_map and records:
            matched = sorted({r.metric for r in records})
            ids = sorted({str(r.get("item_id") or r.get("item_en")) for r in rows})
            _LOG.info(
                "vnstock[%s] %s %s long-form matched=%s years=%s item_ids=%s",
                source,
                upper,
                dataset,
                matched,
                sorted(set(year_map.values()), reverse=True),
                ids[:80],
            )
        elif not records and year_map:
            labels = sorted(
                {str(r.get("item_id") or r.get("item_en") or r.get("item")) for r in rows}
            )
            _LOG.warning(
                "vnstock[%s] %s %s matched 0 metrics (long form, %d rows); years=%s metric_ids=%s",
                source,
                upper,
                dataset,
                len(rows),
                sorted(set(year_map.values()), reverse=True),
                labels[:80],
            )
        elif not records:
            sample = rows[0]
            _LOG.warning(
                "vnstock[%s] %s %s matched 0 metrics (wide form, %d rows); columns=%s sample=%s",
                source,
                upper,
                dataset,
                len(rows),
                list(sample.keys()),
                {k: sample[k] for k in list(sample)[:20]},
            )
        return records

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
