"""Company sync — payload builder + orchestrator (no network).

Fake provider + in-memory repos verify: provider ratio records → VnFundamentals
payload (reusing the domain scorer), profile upsert into the companies table,
and per-symbol tolerance.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from company.application.company_sync import build_fundamentals_payload, sync_companies
from company.domain.company import Company
from providers.sdk.models import CompanyProfile, FundamentalRecord, SectorMapping


def _records(ticker: str) -> tuple[FundamentalRecord, ...]:
    def rec(period: str, metric: str, value: str) -> FundamentalRecord:
        return FundamentalRecord(ticker=ticker, period=period, metric=metric, value=Decimal(value))

    return (
        rec("2025FY", "roe", "0.21"),
        rec("2025FY", "roa", "0.09"),
        rec("2025FY", "net_margin", "0.16"),
        rec("2025FY", "pe", "9.5"),
        rec("2025FY", "pb", "1.6"),
        rec("2025FY", "eps", "4200"),
        rec("2025FY", "revenue", "1200"),
        rec("2024FY", "eps", "3600"),
        rec("2024FY", "revenue", "1000"),
    )


class TestBuildPayload:
    def test_maps_ratios_and_scores(self) -> None:
        payload = build_fundamentals_payload(
            "FPT", _records("FPT"), exchange="HOSE", sector="TECHNOLOGY"
        )
        assert payload["ticker"] == "FPT"
        assert payload["exchange"] == "HOSE" and payload["sector"] == "TECHNOLOGY"
        ratios = payload["ratios"]
        assert ratios["roe"] == 0.21 and ratios["pe"] == 9.5
        assert ratios["operating_margin"] is None  # not in the provider set
        # scores are computed (explainable domain scorer)
        assert isinstance(payload["quality_score"], float)
        # growth = latest vs prior period
        assert payload["revenue_growth_yoy"] == 0.2  # 1200 vs 1000
        assert abs(float(payload["eps_growth_yoy"]) - (4200 - 3600) / 3600) < 1e-9

    def test_empty_records_yields_null_ratios(self) -> None:
        payload = build_fundamentals_payload("ZZZ", ())
        assert payload["ratios"]["roe"] is None
        assert payload["revenue_growth_yoy"] is None


class _MemCompanies:
    def __init__(self) -> None:
        self.saved: dict[str, Company] = {}

    def save(self, company: Company) -> None:
        self.saved[company.ticker] = company

    def get_by_ticker(self, ticker: str) -> Company | None:
        return self.saved.get(ticker.upper())


class _MemFundamentals:
    def __init__(self) -> None:
        self.store: dict[str, dict[str, object]] = {}

    def upsert(self, ticker: str, payload: dict[str, object]) -> None:
        self.store[ticker.upper()] = payload

    def get(self, ticker: str) -> dict[str, object] | None:
        return self.store.get(ticker.upper())


class _FakeProvider:
    def __init__(self, *, fail: set[str] | None = None) -> None:
        self.fail = fail or set()

    def profile(self, ticker: str) -> CompanyProfile | None:
        if ticker in self.fail:
            raise RuntimeError("profile boom")
        return CompanyProfile(
            ticker=ticker,
            name=f"{ticker} Corp",
            exchange="HOSE",
            industry="Software",
            sector="TECHNOLOGY",
            profile="",
            website="",
        )

    def classification(self, ticker: str) -> SectorMapping | None:
        return SectorMapping(
            ticker=ticker, sector="TECHNOLOGY", industry="Software", exchange="HOSE"
        )

    def fundamentals(self, ticker: str, as_of: date) -> tuple[FundamentalRecord, ...]:
        if ticker in self.fail:
            raise RuntimeError("fundamentals boom")
        return _records(ticker)


class TestSyncCompanies:
    def test_syncs_profiles_and_fundamentals(self) -> None:
        companies = _MemCompanies()
        funds = _MemFundamentals()
        result = sync_companies(
            ["FPT", "VCB"],
            provider=_FakeProvider(),
            companies=companies,
            fundamentals_repo=funds,
            as_of=date(2026, 7, 21),
        )
        assert result.profiles == 2 and result.fundamentals == 2 and result.failures == 0
        assert companies.get_by_ticker("FPT") is not None
        assert funds.get("VCB")["ratios"]["roe"] == 0.21

    def test_tolerates_a_bad_symbol(self) -> None:
        companies = _MemCompanies()
        funds = _MemFundamentals()
        result = sync_companies(
            ["FPT", "BAD"],
            provider=_FakeProvider(fail={"BAD"}),
            companies=companies,
            fundamentals_repo=funds,
            as_of=date(2026, 7, 21),
        )
        assert result.profiles == 1 and result.fundamentals == 1 and result.failures == 1
        assert funds.get("BAD") is None
