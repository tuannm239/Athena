"""Unit tests — domain events and small contracts (SPEC-03, Domain Events)."""

from __future__ import annotations

import dataclasses
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from behavior.domain.bias import BiasKind
from behavior.domain.events import BehaviorDetected
from company.domain.company import Company
from decision_kernel.domain.events import DecisionCreated
from market.domain.events import (
    BreadthChanged,
    LiquidityChanged,
    MarketRegimeChanged,
    VolatilityChanged,
)
from market.domain.instrument import AssetClass, Instrument, PricePoint
from market.domain.market_context import Regime
from portfolio.domain.events import PortfolioUpdated
from research.domain.research_summary import ResearchSummary
from risk.domain.events import RiskCalculated
from shared_kernel.identifiers import DecisionId, InstrumentId, PortfolioId, RunId, SnapshotId
from shared_kernel.lineage import Lineage
from shared_kernel.money import Currency, Money


class TestDomainEvents:
    def test_events_are_immutable_and_timestamped(self) -> None:
        event = DecisionCreated(decision_id=DecisionId())
        assert event.occurred_at.tzinfo is not None
        with pytest.raises(dataclasses.FrozenInstanceError):
            event.decision_id = DecisionId()  # type: ignore[misc]

    def test_all_spec03_events_construct(self) -> None:
        events = (
            MarketRegimeChanged(regime=Regime.CONTRACTION),
            LiquidityChanged(liquidity_score=Decimal("0.4")),
            BreadthChanged(breadth_score=Decimal("0.5")),
            VolatilityChanged(volatility_score=Decimal("0.6")),
            PortfolioUpdated(portfolio_id=PortfolioId()),
            RiskCalculated(decision_id=DecisionId()),
            BehaviorDetected(bias=BiasKind.HERDING),
        )
        ids = {e.event_id for e in events}
        assert len(ids) == len(events)


class TestResearchSummary:
    def test_requires_subject_and_sources(self) -> None:
        with pytest.raises(ValueError):
            ResearchSummary(subject="", content="c", sources=("s",))
        with pytest.raises(ValueError):
            ResearchSummary(subject="s", content="c", sources=())

    def test_valid_summary(self) -> None:
        summary = ResearchSummary(subject="ABC 10-K", content="…", sources=("10-K",))
        assert summary.sources == ("10-K",)


class TestMarketContracts:
    def test_instrument_requires_symbol(self) -> None:
        with pytest.raises(ValueError):
            Instrument(
                id=InstrumentId(),
                symbol="",
                name="x",
                asset_class=AssetClass.EQUITY,
                currency=Currency.VND,
            )

    def test_price_point_must_be_positive(self) -> None:
        with pytest.raises(ValueError):
            PricePoint(
                instrument_id=InstrumentId(),
                as_of=datetime.now(timezone.utc),
                close=Money(Decimal("0"), Currency.VND),
            )


class TestCompany:
    def test_requires_ticker_and_name(self) -> None:
        with pytest.raises(ValueError):
            Company(
                ticker="",
                name="ABC Corp",
                exchange="HOSE",
                sector="Materials",
                industry="Steel",
                currency=Currency.VND,
            )

    def test_scores_are_optional(self) -> None:
        company = Company(
            ticker="ABC",
            name="ABC Corp",
            exchange="HOSE",
            sector="Materials",
            industry="Steel",
            currency=Currency.VND,
        )
        assert company.quality_score is None and company.status == "active"


class TestLineage:
    def test_lineage_is_value_object(self) -> None:
        run, snap = RunId(), SnapshotId()
        assert Lineage(run, snap) == Lineage(run, snap)
