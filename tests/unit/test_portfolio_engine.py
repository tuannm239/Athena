"""Unit tests — Portfolio Engine ALG-007/008 (SPEC-10; RFC-0027 §5)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from portfolio.domain.constraints import PortfolioConstraints
from portfolio.domain.optimizer import Candidate, propose_portfolio
from portfolio.domain.sizing import SizingError, kelly_fraction, position_size
from shared_kernel.identifiers import DecisionId
from shared_kernel.measures import Percentage
from shared_kernel.probability import Confidence, Probability


def candidate(
    ticker: str,
    utility: str,
    *,
    sector: str = "tech",
    posterior: str = "0.6",
    ret: str = "0.2",
    dd: str = "0.1",
) -> Candidate:
    return Candidate(
        decision_id=DecisionId(),
        ticker=ticker,
        sector=sector,
        posterior=Probability(Decimal(posterior)),
        confidence=Confidence(Decimal("0.8")),
        expected_return=Decimal(ret),
        expected_drawdown=Decimal(dd),
        expected_utility=Decimal(utility),
    )


class TestKelly:
    def test_formula(self) -> None:
        # p=0.6, b=2 -> 0.6 - 0.4/2 = 0.4
        assert kelly_fraction(
            Probability(Decimal("0.6")), Decimal("0.2"), Decimal("0.1")
        ) == Decimal("0.4")

    def test_never_negative(self) -> None:
        assert kelly_fraction(
            Probability(Decimal("0.1")), Decimal("0.1"), Decimal("0.1")
        ) == Decimal(0)

    def test_invalid_inputs(self) -> None:
        with pytest.raises(SizingError):
            kelly_fraction(Probability(Decimal("0.6")), Decimal("0"), Decimal("0.1"))


class TestPositionSize:
    def test_full_chain(self) -> None:
        size = position_size(
            posterior=Probability(Decimal("0.6")),
            expected_return=Decimal("0.2"),
            expected_drawdown=Decimal("0.1"),
            risk_budget=Decimal("0.5"),
            liquidity_factor=Decimal("0.5"),
            confidence=Confidence(Decimal("0.5")),
        )
        assert size.value == Decimal("0.4") * Decimal("0.5") * Decimal("0.5") * Decimal("0.5")

    def test_constraint_cap(self) -> None:
        size = position_size(
            posterior=Probability(Decimal("0.9")),
            expected_return=Decimal("0.5"),
            expected_drawdown=Decimal("0.05"),
            risk_budget=Decimal(1),
            liquidity_factor=Decimal(1),
            confidence=Confidence(Decimal(1)),
            max_position_weight=Decimal("0.1"),
        )
        assert size.value == Decimal("0.1")

    def test_budget_range_enforced(self) -> None:
        with pytest.raises(SizingError):
            position_size(
                posterior=Probability(Decimal("0.6")),
                expected_return=Decimal("0.2"),
                expected_drawdown=Decimal("0.1"),
                risk_budget=Decimal("1.5"),
                liquidity_factor=Decimal(1),
                confidence=Confidence(Decimal(1)),
            )


class TestOptimizer:
    def test_utility_priority_and_determinism(self) -> None:
        candidates = (
            candidate("BBB", "0.05"),
            candidate("AAA", "0.10"),
            candidate("CCC", "0.10"),
        )
        proposal = propose_portfolio(
            candidates,
            constraints=PortfolioConstraints(max_position_weight=Percentage(Decimal("0.1"))),
            risk_budget=Decimal(1),
        )
        # utility desc, tie AAA before CCC
        assert [a.ticker for a in proposal.allocations] == ["AAA", "CCC", "BBB"]
        again = propose_portfolio(
            candidates,
            constraints=PortfolioConstraints(max_position_weight=Percentage(Decimal("0.1"))),
            risk_budget=Decimal(1),
        )
        assert again == proposal

    def test_negative_utility_never_allocated(self) -> None:
        proposal = propose_portfolio(
            (candidate("AAA", "-0.05"),),
            constraints=PortfolioConstraints(),
            risk_budget=Decimal(1),
        )
        assert proposal.allocations == ()
        assert proposal.expected_utility == Decimal(0)

    def test_cash_never_negative_and_reserve_respected(self) -> None:
        constraints = PortfolioConstraints(min_cash_reserve=Percentage(Decimal("0.5")))
        proposal = propose_portfolio(
            tuple(
                candidate(f"T{i}", "0.10", posterior="0.9", ret="0.5", dd="0.05") for i in range(5)
            ),
            constraints=constraints,
            risk_budget=Decimal(1),
        )
        assert proposal.cash_weight >= Decimal("0.5")
        total = sum((a.weight for a in proposal.allocations), Decimal(0))
        assert total + proposal.cash_weight == Decimal(1)

    def test_sector_exposure_cap(self) -> None:
        constraints = PortfolioConstraints(
            max_position_weight=Percentage(Decimal("0.3")),
            max_sector_exposure=Percentage(Decimal("0.35")),
        )
        proposal = propose_portfolio(
            (
                candidate("AAA", "0.10", posterior="0.9", ret="0.5", dd="0.05"),
                candidate("BBB", "0.09", posterior="0.9", ret="0.5", dd="0.05"),
                candidate("CCC", "0.08", posterior="0.9", ret="0.5", dd="0.05"),
            ),
            constraints=constraints,
            risk_budget=Decimal(1),
        )
        tech = sum((a.weight for a in proposal.allocations), Decimal(0))
        assert tech <= Decimal("0.35")
        assert any("sector" in v for v in proposal.constraint_violations)

    def test_utility_non_negative_versus_cash(self) -> None:
        proposal = propose_portfolio(
            (candidate("AAA", "0.10"), candidate("BBB", "-1")),
            constraints=PortfolioConstraints(),
            risk_budget=Decimal("0.5"),
        )
        assert proposal.expected_utility >= Decimal(0)
        assert proposal.explanation
