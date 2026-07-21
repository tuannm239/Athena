"""Company sync — profiles + fundamentals from the provider into persistence.

Maps the provider's fundamental *records* (roe, roa, pe, pb, eps, …) into the
domain `FundamentalRatios`, reuses the domain's explainable `quality_score`
(no scoring re-implemented), and produces the read-model payload the company
API/frontend consumes (`VnFundamentals` shape). Per-symbol tolerant so one bad
ticker never aborts a company sync.

No business logic lives here beyond mapping + calling the existing domain
scorer; controllers never call the provider (this runs from the sync CLI).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol

from company.domain.company import Company
from company.domain.fundamentals import FundamentalRatios, growth, quality_score
from company.domain.repository import CompanyRepository
from providers.sdk.models import CompanyProfile, FundamentalRecord, SectorMapping
from shared_kernel.money import Currency

_LOG = logging.getLogger("athena.company.sync")


class CompanyDataProvider(Protocol):
    """The provider capabilities a company sync needs (VnstockProvider fits)."""

    def profile(self, ticker: str) -> CompanyProfile | None: ...

    def classification(self, ticker: str) -> SectorMapping | None: ...

    def fundamentals(self, ticker: str, as_of: date) -> tuple[FundamentalRecord, ...]: ...


class FundamentalsRepository(Protocol):
    def upsert(self, ticker: str, payload: dict[str, object]) -> None: ...

    def get(self, ticker: str) -> dict[str, object] | None: ...


def _f(value: Decimal | None) -> float | None:
    return None if value is None else float(value)


def _period_metrics(records: tuple[FundamentalRecord, ...]) -> list[tuple[str, dict[str, Decimal]]]:
    """Group records by period → [(period, {metric: value})], newest period first."""
    by_period: dict[str, dict[str, Decimal]] = {}
    for r in records:
        by_period.setdefault(r.period, {})[r.metric] = r.value
    return sorted(by_period.items(), key=lambda kv: kv[0], reverse=True)


def _ratios_from(metrics: dict[str, Decimal]) -> FundamentalRatios:
    def g(name: str) -> Decimal | None:
        return metrics.get(name)

    return FundamentalRatios(
        roe=g("roe"),
        roa=g("roa"),
        gross_margin=g("gross_margin"),
        operating_margin=None,  # not in the provider ratio set
        net_margin=g("net_margin"),
        debt_to_equity=g("debt_to_equity"),
        current_ratio=g("current_ratio"),
        free_cash_flow=None,
        eps=g("eps"),
        bvps=g("bvps"),
        pe=g("pe"),
        pb=g("pb"),
        ev_ebitda=None,
    )


def build_fundamentals_payload(
    ticker: str,
    records: tuple[FundamentalRecord, ...],
    *,
    exchange: str = "",
    sector: str = "",
) -> dict[str, object]:
    """Build the VnFundamentals read-model payload from provider ratio records.

    Scores come from the domain's `quality_score` (explainable); growth is the
    latest-vs-prior period change in revenue and EPS when both are present.
    """
    periods = _period_metrics(records)
    latest = periods[0][1] if periods else {}
    prior = periods[1][1] if len(periods) > 1 else {}

    ratios = _ratios_from(latest)
    revenue_growth = growth(latest.get("revenue"), prior.get("revenue"))
    eps_growth = growth(latest.get("eps"), prior.get("eps"))
    scores = quality_score(ratios, revenue_growth=revenue_growth, eps_growth=eps_growth)

    return {
        "ticker": ticker.upper(),
        "exchange": exchange,
        "sector": sector,
        "ratios": {
            "roe": _f(ratios.roe),
            "roa": _f(ratios.roa),
            "gross_margin": _f(ratios.gross_margin),
            "operating_margin": _f(ratios.operating_margin),
            "net_margin": _f(ratios.net_margin),
            "debt_to_equity": _f(ratios.debt_to_equity),
            "current_ratio": _f(ratios.current_ratio),
            "free_cash_flow": _f(ratios.free_cash_flow),
            "eps": _f(ratios.eps),
            "bvps": _f(ratios.bvps),
            "pe": _f(ratios.pe),
            "pb": _f(ratios.pb),
            "ev_ebitda": _f(ratios.ev_ebitda),
        },
        "quality_score": _f(scores.quality),
        "valuation_score": _f(scores.valuation),
        "growth_score": _f(scores.growth),
        "revenue_growth_yoy": _f(revenue_growth),
        "eps_growth_yoy": _f(eps_growth),
    }


@dataclass(frozen=True, slots=True)
class CompanySyncResult:
    profiles: int
    fundamentals: int
    failures: int

    def as_dict(self) -> dict[str, object]:
        return {
            "command": "sync.companies",
            "profiles": self.profiles,
            "fundamentals": self.fundamentals,
            "failures": self.failures,
        }


def sync_companies(
    symbols: list[str],
    *,
    provider: CompanyDataProvider,
    companies: CompanyRepository,
    fundamentals_repo: FundamentalsRepository,
    as_of: date,
) -> CompanySyncResult:
    """Sync each symbol's profile + fundamentals; tolerant per symbol."""
    profiles = funds = failures = 0
    for raw in symbols:
        ticker = raw.strip().upper()
        if not ticker:
            continue
        exchange = sector = ""
        try:
            profile = provider.profile(ticker)
            mapping = provider.classification(ticker)
            exchange = (profile.exchange if profile else "") or (
                mapping.exchange if mapping else ""
            )
            sector = (profile.sector if profile else "") or (mapping.sector if mapping else "")
            if profile is not None and profile.name:
                companies.save(
                    Company(
                        ticker=ticker,
                        name=profile.name,
                        exchange=exchange or "HOSE",
                        sector=sector or "OTHER",
                        industry=(profile.industry or (mapping.industry if mapping else "")) or "",
                        currency=Currency.VND,
                    )
                )
                profiles += 1
        except Exception as error:  # noqa: BLE001 — tolerate one bad ticker
            _LOG.warning("company.profile_failed %s: %s: %s", ticker, type(error).__name__, error)

        try:
            records = provider.fundamentals(ticker, as_of)
            if records:
                fundamentals_repo.upsert(
                    ticker,
                    build_fundamentals_payload(ticker, records, exchange=exchange, sector=sector),
                )
                funds += 1
        except Exception as error:  # noqa: BLE001 — tolerate one bad ticker
            failures += 1
            _LOG.warning(
                "company.fundamentals_failed %s: %s: %s", ticker, type(error).__name__, error
            )

    return CompanySyncResult(profiles=profiles, fundamentals=funds, failures=failures)
