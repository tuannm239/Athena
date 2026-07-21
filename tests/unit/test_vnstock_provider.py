"""vnstock provider adapter — VN market (fixtures; no network in CI).

The vnstock library reaches VN data hosts (VCI/TCBS) eagerly, and this
environment's egress proxy blocks them, so the deterministic tests drive
the adapter through a `FakeVnstockClient` seeded with *real-shaped* vnstock
4.x records (the columns vnstock returns). This exercises every capability,
the resilience stack, and end-to-end storage through the Data Pipeline
without a network. A live smoke test is included but skipped unless
VNSTOCK_LIVE=1 (run it on open internet — locally or on Render).
"""

from __future__ import annotations

import os
from datetime import date
from decimal import Decimal

import pytest

# reuse the in-memory pipeline harness from the production-sync test suite
from tests.unit.test_production_sync import MemoryCatalog, MemorySnapshots

from data_pipeline.application.sync import (
    FUNDAMENTALS_DATASET,
    PRICES_DATASET,
    ProviderSyncService,
)
from data_pipeline.application.use_cases import DataPipelineUseCases
from data_pipeline.domain.dataset import DatasetStatus
from providers.connectors.resilience import ProviderCallError, RetryPolicy
from providers.connectors.resilient import ResilientPriceProvider
from providers.connectors.vnstock_provider import (
    RealVnstockClient,
    VnstockError,
    VnstockProvider,
    create_vnstock_price_provider,
    create_vnstock_sector_provider,
)
from providers.registry_config import VNSTOCK, build_registry
from providers.sdk.registry import Capability

Record = dict[str, object]


# ---- recorded, real-shaped vnstock 4.x responses --------------------------
HISTORY_FPT: list[Record] = [
    {
        "time": "2026-01-05",
        "open": 138.0,
        "high": 139.5,
        "low": 137.2,
        "close": 138.4,
        "volume": 4_900_000,
    },
    {
        "time": "2026-01-06",
        "open": 138.4,
        "high": 141.0,
        "low": 138.1,
        "close": 140.6,
        "volume": 5_300_000,
    },
    {
        "time": "2025-12-31",
        "open": 136.0,
        "high": 137.0,
        "low": 135.5,
        "close": 136.8,
        "volume": 3_800_000,
    },
]
HISTORY_VNINDEX: list[Record] = [
    {
        "time": "2026-01-05",
        "open": 1280.1,
        "high": 1288.0,
        "low": 1278.4,
        "close": 1284.56,
        "volume": 620_000_000,
    },
    {
        "time": "2026-01-06",
        "open": 1284.6,
        "high": 1295.2,
        "low": 1283.0,
        "close": 1293.11,
        "volume": 655_000_000,
    },
]
ALL_SYMBOLS: list[Record] = [
    {"ticker": "FPT", "organ_name": "FPT Corporation", "exchange": "HSX"},
    {"ticker": "HPG", "organ_name": "Hoa Phat Group JSC", "exchange": "HSX"},
    {"ticker": "SHS", "organ_name": "Saigon-Hanoi Securities", "exchange": "HNX"},
]
INDUSTRIES: list[Record] = [
    {
        "symbol": "FPT",
        "organ_name": "FPT Corporation",
        "icb_name2": "Technology",
        "icb_name3": "Software & Computer Services",
        "icb_name4": "Software",
        "exchange": "HSX",
    },
    {
        "symbol": "HPG",
        "organ_name": "Hoa Phat Group JSC",
        "icb_name2": "Basic Materials",
        "icb_name3": "Industrial Metals & Mining",
        "icb_name4": "Iron & Steel",
        "exchange": "HSX",
    },
]
OVERVIEW_FPT: list[Record] = [
    {
        "symbol": "FPT",
        "organ_name": "FPT Corporation",
        "exchange": "HSX",
        "icb_name2": "Technology",
        "icb_name4": "Software",
        "company_profile": "FPT is a leading Vietnamese ICT corporation.",
        "website": "https://fpt.com.vn",
    },
]
RATIOS_FPT: list[Record] = [
    {
        "year": 2025,
        "roe": 0.243,
        "roa": 0.121,
        "pe": 18.6,
        "pb": 3.9,
        "eps": 5200,
        "gross_margin": 0.39,
        "net_margin": 0.163,
        "debt_to_equity": 0.41,
        "current_ratio": 1.32,
    },
    {
        "year": 2024,
        "roe": 0.228,
        "roa": 0.114,
        "pe": 16.1,
        "pb": 3.4,
        "eps": 4550,
        "gross_margin": 0.38,
        "net_margin": 0.157,
        "debt_to_equity": 0.44,
        "current_ratio": 1.28,
    },
]


class FakeVnstockClient:
    """Scripted vnstock client — real-shaped records, no network."""

    def __init__(
        self,
        *,
        history: dict[str, list[Record]] | None = None,
        ratios: dict[str, list[Record]] | None = None,
        income: dict[str, list[Record]] | None = None,
        balance: dict[str, list[Record]] | None = None,
    ) -> None:
        self._history = history or {"FPT": HISTORY_FPT, "VNINDEX": HISTORY_VNINDEX}
        self._ratios = ratios
        self._income = income or {}
        self._balance = balance or {}
        self.calls: list[str] = []

    def history(self, symbol: str, start: str, end: str, interval: str) -> list[Record]:
        self.calls.append(f"history:{symbol}")
        return self._history.get(symbol.upper(), [])

    def all_symbols(self) -> list[Record]:
        self.calls.append("all_symbols")
        return ALL_SYMBOLS

    def industries(self) -> list[Record]:
        self.calls.append("industries")
        return INDUSTRIES

    def company_overview(self, symbol: str) -> list[Record]:
        self.calls.append(f"overview:{symbol}")
        return OVERVIEW_FPT if symbol.upper() == "FPT" else []

    def financial_ratios(self, symbol: str, period: str) -> list[Record]:
        self.calls.append(f"ratios:{symbol}:{period}")
        if self._ratios is not None:
            return self._ratios.get(symbol.upper(), [])
        return RATIOS_FPT if symbol.upper() == "FPT" else []

    def income_statement(self, symbol: str, period: str) -> list[Record]:
        self.calls.append(f"income:{symbol}:{period}")
        return self._income.get(symbol.upper(), [])

    def balance_sheet(self, symbol: str, period: str) -> list[Record]:
        self.calls.append(f"balance:{symbol}:{period}")
        return self._balance.get(symbol.upper(), [])


class FlakyClient(FakeVnstockClient):
    """Fails `fail_times` before succeeding — exercises retry/backoff."""

    def __init__(self, fail_times: int) -> None:
        super().__init__()
        self._left = fail_times

    def history(self, symbol: str, start: str, end: str, interval: str) -> list[Record]:
        if self._left > 0:
            self._left -= 1
            raise VnstockError("transient upstream error")
        return super().history(symbol, start, end, interval)


@pytest.fixture()
def provider() -> VnstockProvider:
    return VnstockProvider(client=FakeVnstockClient())


# ---- Historical OHLCV -----------------------------------------------------
class TestOhlcv:
    def test_daily_bars_parse_and_window(self, provider: VnstockProvider) -> None:
        bars = provider.daily_bars("FPT", date(2026, 1, 1), date(2026, 1, 31))
        assert [b.day.isoformat() for b in bars] == [
            "2026-01-05",
            "2026-01-06",
        ]  # 2025 row excluded
        assert bars[0].close == Decimal("138.4")
        assert bars[0].open == Decimal("138.0")
        assert bars[0].volume == Decimal("4900000")
        assert all(b.ticker == "FPT" for b in bars)

    def test_daily_bars_sorted(self, provider: VnstockProvider) -> None:
        bars = provider.daily_bars("FPT", date(2025, 12, 1), date(2026, 1, 31))
        assert [b.day for b in bars] == sorted(b.day for b in bars)


# ---- VNINDEX / VN30 (indices are symbols) ---------------------------------
class TestIndices:
    def test_vnindex_series(self, provider: VnstockProvider) -> None:
        bars = provider.daily_bars("VNINDEX", date(2026, 1, 1), date(2026, 1, 31))
        assert bars[-1].close == Decimal("1293.11")
        assert bars[0].ticker == "VNINDEX"

    def test_vn30_via_history_map(self) -> None:
        p = VnstockProvider(client=FakeVnstockClient(history={"VN30": HISTORY_VNINDEX}))
        bars = p.daily_bars("VN30", date(2026, 1, 1), date(2026, 1, 31))
        assert len(bars) == 2 and bars[0].ticker == "VN30"


# ---- Financial Statements -------------------------------------------------
class TestFundamentals:
    def test_ratios_to_records(self, provider: VnstockProvider) -> None:
        recs = provider.fundamentals("FPT", date(2026, 1, 31))
        by = {(r.period, r.metric): r.value for r in recs}
        assert by[("2025FY", "roe")] == Decimal("0.243")
        assert by[("2025FY", "pe")] == Decimal("18.6")
        assert by[("2024FY", "eps")] == Decimal("4550")
        assert all(r.ticker == "FPT" for r in recs)

    def test_unknown_ticker_empty(self, provider: VnstockProvider) -> None:
        assert provider.fundamentals("ZZZ", date(2026, 1, 31)) == ()

    def test_vci_long_transposed_frame(self) -> None:
        """The real VCI ratio frame is *long*: one row per metric, one column
        per year ('item', 'item_en', 'item_id', '2018'…'2025'). The metric-per-
        row parser must read each year column into a period record."""
        long_rows: list[Record] = [
            {"item": "Năm", "item_en": None, "item_id": "year", "2025": "2025", "2024": "2024"},
            {"item": "ROE", "item_en": "ROE (%)", "item_id": "roe", "2025": 0.28, "2024": 0.26},
            {"item": "P/E", "item_en": "P/E", "item_id": "pe", "2025": 15.2, "2024": 16.0},
            {"item": "EPS", "item_en": "EPS", "item_id": "eps", "2025": 5100, "2024": 4800},
        ]
        provider = VnstockProvider(client=FakeVnstockClient(ratios={"VNM": long_rows}))
        by = {(r.period, r.metric): r.value for r in provider.fundamentals("VNM", date.today())}
        assert by[("2025FY", "roe")] == Decimal("0.28")
        assert by[("2024FY", "roe")] == Decimal("0.26")
        assert by[("2025FY", "pe")] == Decimal("15.2")
        assert by[("2024FY", "eps")] == Decimal("4800")
        # the 'year' metadata row is not a metric
        assert not any(m == "year" for (_, m) in by)

    def test_vci_duplicate_year_headers_read_from_year_row(self) -> None:
        """VCI ships every year column with the *same* header ('2018'); after
        `_records` de-dups them to '2018','2018.1',… the true years live only in
        the 'year' row, so periods must be keyed off that row's values — and all
        years must survive (the Growth tab needs more than one)."""
        rows: list[Record] = [
            {"item": "Năm", "item_en": None, "item_id": "year", "2018": "2025", "2018.1": "2024"},
            {"item": "ROE", "item_en": "ROE", "item_id": "roe", "2018": 0.30, "2018.1": 0.27},
            {
                "item": "EV/EBITDA",
                "item_en": "EV/EBITDA",
                "item_id": "ev_to_ebitda",
                "2018": 11.0,
                "2018.1": 10.0,
            },
        ]
        provider = VnstockProvider(client=FakeVnstockClient(ratios={"FPT": rows}))
        by = {(r.period, r.metric): r.value for r in provider.fundamentals("FPT", date.today())}
        assert by[("2025FY", "roe")] == Decimal("0.30")
        assert by[("2024FY", "roe")] == Decimal("0.27")  # prior year not lost
        assert by[("2025FY", "ev_ebitda")] == Decimal("11.0")  # ev_to_ebitda mapped

    def test_merges_income_statement_and_balance_sheet(self) -> None:
        """Real VCI vocabulary: income statement carries revenue ('sales'/
        'net_sales'), net income and EPS ('eps_basic_vnd'); the balance sheet
        carries owners' equity and shares. `fundamentals` must pull all three
        and map them so revenue/EPS growth and the book-value inputs land."""
        ratio = [
            {"item": "Năm", "item_id": "year", "2018": "2025", "2018.1": "2024"},
            {"item": "ROE", "item_id": "roe", "2018": 0.28, "2018.1": 0.26},
            {"item": "Shares", "item_id": "outstanding_shares", "2018": 1000, "2018.1": 1000},
        ]
        income = [
            {"item": "Sales", "item_id": "net_sales", "2025": 1200, "2024": 1000},
            {"item": "NPAT", "item_id": "attributable_to_parent_company", "2025": 200, "2024": 160},
            {"item": "EPS", "item_id": "eps_basic_vnd", "2025": 5100, "2024": 4200},
        ]
        balance = [
            {"item": "Vốn CSH", "item_id": "owners_equity", "2025": 19000, "2024": 17000},
        ]
        provider = VnstockProvider(
            client=FakeVnstockClient(
                ratios={"FPT": ratio}, income={"FPT": income}, balance={"FPT": balance}
            )
        )
        by = {(r.period, r.metric): r.value for r in provider.fundamentals("FPT", date.today())}
        assert by[("2025FY", "roe")] == Decimal("0.28")  # ratio
        assert by[("2025FY", "revenue")] == Decimal("1200")  # income: net_sales
        assert by[("2024FY", "revenue")] == Decimal("1000")
        assert by[("2025FY", "eps")] == Decimal("5100")  # income: eps_basic_vnd
        assert by[("2025FY", "owners_equity")] == Decimal("19000")  # balance sheet
        assert by[("2025FY", "shares")] == Decimal("1000")  # ratio

    def test_statement_year_named_columns_no_year_row(self) -> None:
        """The income statement / balance sheet name their columns by year
        ('2025','2024',…) and carry NO 'year' row — the headers are the years.
        Parsing must key periods off those headers, not require a year row."""
        income = [
            {
                "item": "Doanh thu",
                "item_en": "Sales",
                "item_id": "sales",
                "2025": 70207688944553.0,
                "2024": 62962652134635.0,
            },
        ]
        provider = VnstockProvider(client=FakeVnstockClient(income={"FPT": income}, ratios={}))
        by = {(r.period, r.metric): r.value for r in provider.fundamentals("FPT", date.today())}
        assert by[("2025FY", "revenue")] == Decimal("70207688944553.0")
        assert by[("2024FY", "revenue")] == Decimal("62962652134635.0")

    def test_records_dedupes_duplicate_column_labels(self) -> None:
        """`_records` must keep every column's values when the vendor repeats a
        column label (VCI's duplicate year headers) instead of collapsing them."""
        pd = pytest.importorskip("pandas")
        frame = pd.DataFrame([[1, 2, 3]], columns=["2018", "2018", "b"])
        assert RealVnstockClient._records(frame) == [{"2018": 1, "2018.1": 2, "b": 3}]

    def test_vci_multiindex_flattened_columns(self) -> None:
        """Real VCI ratio frames arrive as MultiIndex columns flattened to
        ``group_leaf`` with unit suffixes (``ROE (%)``, ``P/E``, ``EPS (VND)``).
        The canonical matcher must still extract them (the exact-string table
        silently produced zero records — the empty-tab bug)."""
        vci_rows: list[Record] = [
            {
                "Meta_ticker": "VNM",
                "Meta_yearReport": 2025,
                "Chỉ tiêu khả năng sinh lợi_ROE (%)": 0.28,
                "Chỉ tiêu khả năng sinh lợi_ROA (%)": 0.19,
                "Chỉ tiêu định giá_P/E": 15.2,
                "Chỉ tiêu định giá_P/B": 4.1,
                "Chỉ tiêu định giá_EPS (VND)": 5100,
                "Chỉ tiêu định giá_BVPS (VND)": 19000,
                "Chỉ tiêu khả năng sinh lợi_Net Profit Margin (%)": 0.17,
                "Chỉ tiêu thanh khoản_Debt/Equity": 0.32,
                "Chỉ tiêu thanh khoản_Current Ratio": 2.1,
            },
        ]
        provider = VnstockProvider(client=FakeVnstockClient(ratios={"VNM": vci_rows}))
        by = {(r.period, r.metric): r.value for r in provider.fundamentals("VNM", date.today())}
        assert by[("2025FY", "roe")] == Decimal("0.28")
        assert by[("2025FY", "pe")] == Decimal("15.2")
        assert by[("2025FY", "eps")] == Decimal("5100")
        assert by[("2025FY", "bvps")] == Decimal("19000")
        assert by[("2025FY", "net_margin")] == Decimal("0.17")
        assert by[("2025FY", "debt_to_equity")] == Decimal("0.32")
        assert by[("2025FY", "current_ratio")] == Decimal("2.1")


# ---- Industry Classification ----------------------------------------------
class TestSector:
    def test_classification(self, provider: VnstockProvider) -> None:
        m = provider.classification("HPG")
        assert m is not None
        assert m.sector == "Basic Materials"
        assert m.industry == "Iron & Steel"
        assert m.exchange == "HSX"

    def test_classification_missing(self, provider: VnstockProvider) -> None:
        assert provider.classification("ZZZ") is None


# ---- Symbol List ----------------------------------------------------------
class TestSymbols:
    def test_symbol_list(self, provider: VnstockProvider) -> None:
        syms = provider.symbols()
        codes = {s.ticker for s in syms}
        assert {"FPT", "HPG", "SHS"} <= codes
        fpt = next(s for s in syms if s.ticker == "FPT")
        assert fpt.name == "FPT Corporation" and fpt.exchange == "HSX"


# ---- Company Profile ------------------------------------------------------
class TestProfile:
    def test_profile(self, provider: VnstockProvider) -> None:
        p = provider.profile("FPT")
        assert p is not None
        assert p.name == "FPT Corporation"
        assert p.sector == "Technology"
        assert "ICT" in p.profile or "FPT" in p.profile
        assert p.website == "https://fpt.com.vn"

    def test_profile_missing(self, provider: VnstockProvider) -> None:
        assert provider.profile("ZZZ") is None


# ---- Resilience: retry + cache --------------------------------------------
class TestResilience:
    def test_retry_then_succeed(self) -> None:
        resilient = ResilientPriceProvider(
            inner=VnstockProvider(client=FlakyClient(fail_times=2)),
            retry=RetryPolicy(max_attempts=4, base_delay_seconds=0.0),
        )
        bars = resilient.daily_bars("FPT", date(2026, 1, 1), date(2026, 1, 31))
        assert len(bars) == 2
        assert resilient.status().healthy is True

    def test_retry_exhausted_raises(self) -> None:
        resilient = ResilientPriceProvider(
            inner=VnstockProvider(client=FlakyClient(fail_times=99)),
            retry=RetryPolicy(max_attempts=3, base_delay_seconds=0.0),
        )
        with pytest.raises(ProviderCallError):
            resilient.daily_bars("FPT", date(2026, 1, 1), date(2026, 1, 31))
        assert resilient.status().consecutive_failures >= 1

    def test_cache_avoids_second_call(self) -> None:
        client = FakeVnstockClient()
        resilient = create_vnstock_price_provider(client=client)
        first = resilient.daily_bars("FPT", date(2026, 1, 1), date(2026, 1, 31))
        second = resilient.daily_bars("FPT", date(2026, 1, 1), date(2026, 1, 31))
        assert first == second
        assert client.calls.count("history:FPT") == 1  # served from cache the 2nd time


# ---- Registry wiring ------------------------------------------------------
class TestRegistry:
    def test_vnstock_registered_for_vn_capabilities(self) -> None:
        registry = build_registry()
        for cap in (Capability.PRICE, Capability.FUNDAMENTAL, Capability.SECTOR):
            assert VNSTOCK in registry.names(cap)

    def test_resolve_sector_provider(self) -> None:
        # Factory is lazy and injectable — resolve without touching the network.
        prov = create_vnstock_sector_provider(client=FakeVnstockClient())
        assert prov.classification("FPT") is not None


# ---- Data Pipeline storage (requirement 6) --------------------------------
class TestPipelineStorage:
    def _sync(self) -> tuple[ProviderSyncService, DataPipelineUseCases]:
        pipeline = DataPipelineUseCases(catalog=MemoryCatalog(), snapshots=MemorySnapshots())
        return ProviderSyncService(pipeline=pipeline, source="provider:vnstock"), pipeline

    def test_full_sync_prices_stores_published_version(self) -> None:
        sync, pipeline = self._sync()
        provider = VnstockProvider(client=FakeVnstockClient())
        version = sync.full_sync_prices(
            provider, ["FPT", "VNINDEX"], date(2026, 1, 1), date(2026, 1, 31)
        )
        assert version.status is DatasetStatus.PUBLISHED
        frame = pipeline.read_published(PRICES_DATASET)
        tickers = set(frame["ticker"].to_list())
        assert {"FPT", "VNINDEX"} <= tickers

    def test_sync_fundamentals_stores_records(self) -> None:
        sync, pipeline = self._sync()
        provider = VnstockProvider(client=FakeVnstockClient())
        version = sync.sync_fundamentals(provider, ["FPT"], date(2026, 1, 31))
        assert version.status is DatasetStatus.PUBLISHED
        frame = pipeline.read_published(FUNDAMENTALS_DATASET)
        assert "roe" in set(frame["metric"].to_list())


# ---- RealVnstockClient DataFrame → records (pandas, no network) -----------
class TestRecordsNormalization:
    """`RealVnstockClient._records` runs against real pandas frames without any
    network — it is the exact conversion used in production."""

    def test_flat_dataframe_to_records(self) -> None:
        import pandas as pd

        from providers.connectors.vnstock_provider import RealVnstockClient

        frame = pd.DataFrame(
            [{"time": "2026-01-05", "close": 138.4}, {"time": "2026-01-06", "close": 140.6}]
        )
        recs = RealVnstockClient._records(frame)
        assert recs == [
            {"time": "2026-01-05", "close": 138.4},
            {"time": "2026-01-06", "close": 140.6},
        ]

    def test_multiindex_columns_flattened(self) -> None:
        import pandas as pd

        from providers.connectors.vnstock_provider import RealVnstockClient

        frame = pd.DataFrame(
            [[2025, 0.24]], columns=pd.MultiIndex.from_tuples([("Meta", "year"), ("Ratio", "roe")])
        )
        recs = RealVnstockClient._records(frame)
        assert recs == [{"Meta_year": 2025, "Ratio_roe": 0.24}]

    def test_none_is_empty(self) -> None:
        from providers.connectors.vnstock_provider import RealVnstockClient

        assert RealVnstockClient._records(None) == []

    def test_non_tabular_raises(self) -> None:
        from providers.connectors.vnstock_provider import RealVnstockClient

        with pytest.raises(VnstockError):
            RealVnstockClient._records("not a dataframe")


# ---- Resilient fundamental/sector wrappers: cache + health ----------------
class TestResilientFundamentalSector:
    def test_fundamental_cache_and_health(self) -> None:
        from providers.connectors.vnstock_provider import create_vnstock_fundamental_provider

        client = FakeVnstockClient()
        prov = create_vnstock_fundamental_provider(client=client)
        first = prov.fundamentals("FPT", date(2026, 1, 31))
        second = prov.fundamentals("FPT", date(2026, 1, 31))
        assert first == second and first  # non-empty, cached
        assert client.calls.count("ratios:FPT:year") == 1
        assert prov.status().healthy is True

    def test_sector_cache(self) -> None:
        prov = create_vnstock_sector_provider(client=(client := FakeVnstockClient()))
        prov.classification("FPT")
        prov.classification("FPT")
        assert client.calls.count("industries") == 1  # second served from cache


# ---- Live smoke test (opt-in; needs open internet to VN data hosts) -------
@pytest.mark.skipif(
    os.environ.get("VNSTOCK_LIVE") != "1",
    reason="live vnstock call — set VNSTOCK_LIVE=1 on open internet (blocked by CI egress proxy)",
)
class TestLiveSmoke:
    def test_live_vnindex_and_fpt(self) -> None:
        from providers.connectors.vnstock_provider import create_vnstock_provider

        provider = create_vnstock_provider()
        vnindex = provider.daily_bars("VNINDEX", date(2026, 1, 2), date(2026, 1, 10))
        assert vnindex, "expected live VNINDEX bars"
        syms = provider.symbols()
        assert any(s.ticker == "FPT" for s in syms)
