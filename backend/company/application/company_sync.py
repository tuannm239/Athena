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

# Bumped whenever the payload gains fields from a new data source, so a
# `--only-missing` re-run refreshes rows written by an older sync (e.g. the
# ratio-only v1 rows, before income-statement/balance-sheet EPS/BVPS/revenue).
FUNDAMENTALS_SCHEMA_VERSION = 6


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


def _latest_by_metric(records: tuple[FundamentalRecord, ...]) -> dict[str, Decimal]:
    """Each metric → its value from the newest period that carries it.

    Different vnstock datasets label periods differently (the ratio feed can
    report a single, mis-labelled year while the income statement/balance sheet
    carry the real 2022–2025 years), so a single "latest period" would drop
    whichever dataset didn't own it. Taking the newest value *per metric* keeps
    every field regardless of which dataset supplied it.
    """
    merged: dict[str, Decimal] = {}
    for _period, metrics in reversed(_period_metrics(records)):  # oldest→newest wins
        merged.update(metrics)
    return merged


def _growth_by_metric(records: tuple[FundamentalRecord, ...], metric: str) -> Decimal | None:
    """YoY growth for one metric from its two newest periods (units cancel)."""
    values = [metrics[metric] for _p, metrics in _period_metrics(records) if metric in metrics]
    return growth(values[0], values[1]) if len(values) >= 2 else None


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
        ev_ebitda=g("ev_ebitda"),
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
    latest-vs-prior change in revenue and EPS. Metrics are merged per-metric
    across the ratio / income-statement / balance-sheet datasets, so a field is
    taken from whichever dataset most recently reported it.
    """
    latest = _latest_by_metric(records)
    # Derive BVPS when the vendor reports no direct book-value-per-share. VCI's
    # share-count field is not in absolute shares, so equity ÷ shares mis-scales;
    # instead use the identity BVPS = EPS × P/E ÷ P/B (price cancels), which
    # relies only on already-clean per-share/valuation ratios. Explainable and
    # unit-safe. EPS is reported directly (eps_basic_vnd) and needs no derivation.
    if "bvps" not in latest:
        eps, pe, pb = latest.get("eps"), latest.get("pe"), latest.get("pb")
        if eps is not None and pe is not None and pb not in (None, Decimal(0)):
            latest = {**latest, "bvps": eps * pe / pb}  # type: ignore[operator]

    ratios = _ratios_from(latest)
    revenue_growth = _growth_by_metric(records, "revenue")
    eps_growth = _growth_by_metric(records, "eps")
    scores = quality_score(ratios, revenue_growth=revenue_growth, eps_growth=eps_growth)

    return {
        "ticker": ticker.upper(),
        "exchange": exchange,
        "sector": sector,
        "schema_version": FUNDAMENTALS_SCHEMA_VERSION,
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
    """Sync each symbol's profile + fundamentals; tolerant per symbol.

    Emits grep-able per-symbol progress at INFO so a shell-less operator can
    watch the sync converge (and see exactly where it stalls) from the logs —
    the final JSON summary is only reached if the whole batch completes.
    """
    profiles = funds = failures = 0
    total = len(symbols)
    _LOG.info("company.sync start symbols=%d as_of=%s", total, as_of)
    for index, raw in enumerate(symbols, start=1):
        ticker = raw.strip().upper()
        if not ticker:
            continue
        _LOG.info("company.sync [%d/%d] %s begin", index, total, ticker)
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
                _LOG.info(
                    "company.sync [%d/%d] %s ok (%d ratio records persisted)",
                    index,
                    total,
                    ticker,
                    len(records),
                )
            else:
                # No ratio rows came back — the profile may still be saved, but
                # nothing lands in company_fundamentals, so companies_synced
                # will NOT move for this ticker. Surfaced explicitly so an empty
                # provider response is distinguishable from a crash in the logs.
                _LOG.warning(
                    "company.sync [%d/%d] %s no fundamentals (0 ratio records — not persisted)",
                    index,
                    total,
                    ticker,
                )
        except Exception as error:  # noqa: BLE001 — tolerate one bad ticker
            failures += 1
            _LOG.warning(
                "company.fundamentals_failed %s: %s: %s", ticker, type(error).__name__, error
            )

    _LOG.info(
        "company.sync done profiles=%d fundamentals=%d failures=%d", profiles, funds, failures
    )
    return CompanySyncResult(profiles=profiles, fundamentals=funds, failures=failures)
