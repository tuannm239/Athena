"""Unit tests — Market Regime Detection ALG-001 (RFC-0025)."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from infrastructure.events import InProcessEventBus
from infrastructure.market_repository import InMemoryMarketRepository
from market.application.use_cases import MarketUseCases
from market.domain.events import MarketRegimeChanged
from market.domain.market_context import Regime
from market.domain.regime_engine import (
    RegimeInputError,
    RegimeInputs,
    classify,
    evaluate_regime,
    market_score,
    regime_confidence,
)
from shared_kernel.events import DomainEvent
from shared_kernel.exceptions import NotFoundError

AS_OF = datetime(2026, 7, 16, tzinfo=timezone.utc)


def full_inputs(value: str, volatility: str = "20") -> RegimeInputs:
    v = Decimal(value)
    return RegimeInputs(trend=v, breadth=v, liquidity=v, momentum=v, volatility=Decimal(volatility))


class TestMarketScore:
    def test_weighted_formula(self) -> None:
        inputs = RegimeInputs(
            trend=Decimal(80),
            breadth=Decimal(70),
            liquidity=Decimal(60),
            momentum=Decimal(50),
            volatility=Decimal(30),
        )
        expected = (
            Decimal("0.30") * 80
            + Decimal("0.20") * 70
            + Decimal("0.20") * 60
            + Decimal("0.15") * 50
            + Decimal("0.15") * (100 - 30)
        )
        assert market_score(inputs) == expected

    def test_missing_inputs_renormalize_weights(self) -> None:
        only_trend = RegimeInputs(trend=Decimal(90))
        assert market_score(only_trend) == Decimal(90)

    def test_out_of_range_rejected(self) -> None:
        with pytest.raises(RegimeInputError):
            RegimeInputs(trend=Decimal(101))

    def test_all_missing_rejected(self) -> None:
        with pytest.raises(RegimeInputError):
            RegimeInputs()


class TestClassification:
    @pytest.mark.parametrize(
        ("score", "regime"),
        [
            ("80", Regime.EXPANSION),
            ("95", Regime.EXPANSION),
            ("79.99", Regime.RECOVERY),
            ("60", Regime.RECOVERY),
            ("59.99", Regime.CONSOLIDATION),
            ("40", Regime.CONSOLIDATION),
            ("39.99", Regime.CONTRACTION),
            ("0", Regime.CONTRACTION),
        ],
    )
    def test_bands(self, score: str, regime: Regime) -> None:
        assert classify(Decimal(score)) is regime

    def test_all_regimes_reachable_from_inputs(self) -> None:
        assert evaluate_regime(full_inputs("90", volatility="10"), AS_OF).regime is (
            Regime.EXPANSION
        )
        assert evaluate_regime(full_inputs("65", volatility="35"), AS_OF).regime is (
            Regime.RECOVERY
        )
        assert evaluate_regime(full_inputs("50", volatility="50"), AS_OF).regime is (
            Regime.CONSOLIDATION
        )
        assert evaluate_regime(full_inputs("20", volatility="80"), AS_OF).regime is (
            Regime.CONTRACTION
        )


class TestConfidence:
    def test_perfectly_consistent_full_inputs(self) -> None:
        inputs = full_inputs("60", volatility="40")  # adjusted vol = 60 too
        assert regime_confidence(inputs, market_score(inputs)).value == Decimal(1)

    def test_missing_inputs_reduce_confidence(self) -> None:
        full = full_inputs("60", volatility="40")
        partial = RegimeInputs(trend=Decimal(60), breadth=Decimal(60))
        c_full = regime_confidence(full, market_score(full))
        c_partial = regime_confidence(partial, market_score(partial))
        assert c_partial.value < c_full.value

    def test_dispersion_reduces_confidence(self) -> None:
        tight = full_inputs("60", volatility="40")
        wide = RegimeInputs(
            trend=Decimal(100),
            breadth=Decimal(0),
            liquidity=Decimal(100),
            momentum=Decimal(0),
            volatility=Decimal(0),
        )
        assert (
            regime_confidence(wide, market_score(wide)).value
            < regime_confidence(tight, market_score(tight)).value
        )

    def test_determinism(self) -> None:
        inputs = full_inputs("72", volatility="33")
        results = {evaluate_regime(inputs, AS_OF).confidence.value for _ in range(5)}
        assert len(results) == 1


class TestMarketUseCases:
    def _use_cases(self) -> tuple[MarketUseCases, list[DomainEvent]]:
        bus = InProcessEventBus()
        received: list[DomainEvent] = []
        bus.subscribe(MarketRegimeChanged, received.append)
        return MarketUseCases(repository=InMemoryMarketRepository(), events=bus), received

    def test_regime_change_emits_event_once(self) -> None:
        use_cases, received = self._use_cases()
        use_cases.evaluate(full_inputs("90", volatility="10"), as_of=AS_OF)
        assert len(received) == 1  # first evaluation always announces
        use_cases.evaluate(full_inputs("90", volatility="10"), as_of=AS_OF)
        assert len(received) == 1  # unchanged regime: no event
        use_cases.evaluate(full_inputs("20", volatility="80"), as_of=AS_OF)
        assert len(received) == 2

    def test_current_context_roundtrip_and_missing(self) -> None:
        use_cases, _ = self._use_cases()
        with pytest.raises(NotFoundError):
            use_cases.current_context()
        context = use_cases.evaluate(full_inputs("65", volatility="35"), as_of=AS_OF)
        assert use_cases.current_context() == context
