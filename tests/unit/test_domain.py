"""Unit tests for the domain layer (Sprint 1, SPEC-03/04/05/10/11/12)."""

from __future__ import annotations

import dataclasses
import sys
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from behavior.domain.bias import BehaviorReport, BiasKind
from behavior.domain.journal import DecisionJournalEntry
from decision_kernel.domain.decision import (
    Decision,
    DecisionError,
    DecisionStatus,
    InvalidDecisionTransition,
)
from decision_kernel.domain.events import DecisionCreated, DecisionReviewed, EvidenceAdded
from decision_kernel.domain.evidence import Evidence
from identity.domain.user import User
from market.domain.market_context import MarketContext, Regime
from portfolio.domain.portfolio import Portfolio, PortfolioError
from portfolio.domain.position import Position
from risk.domain.risk_assessment import RiskAssessment, RiskLevel
from risk.domain.risk_report import RiskReport
from shared_kernel.identifiers import DecisionId, RunId, SnapshotId, UserId
from shared_kernel.measures import Percentage, PositionSize, TimeRange
from shared_kernel.money import Currency, CurrencyMismatchError, Money
from shared_kernel.probability import (
    Confidence,
    DistributionError,
    Probability,
    ProbabilityDistribution,
)


def evidence(desc: str = "evidence") -> Evidence:
    return Evidence(
        source="unit-test",
        category="fundamental",
        description=desc,
        confidence=Confidence(Decimal("0.8")),
    )


def risk_assessment() -> RiskAssessment:
    return RiskAssessment(
        var=Decimal("0.05"),
        cvar=Decimal("0.08"),
        max_drawdown=Decimal("0.25"),
        stress_score=Decimal("0.4"),
        liquidity_score=Decimal("0.7"),
        level=RiskLevel.MODERATE,
        confidence=Confidence(Decimal("0.9")),
    )


def draft_decision() -> Decision:
    return Decision(
        hypothesis="Company X outperforms its sector over 12 months",
        probability=Probability(Decimal("0.6")),
        confidence=Confidence(Decimal("0.7")),
    )


class TestIdentifiers(unittest.TestCase):
    def test_ids_are_type_strict(self) -> None:
        a, b = RunId(), SnapshotId()
        self.assertNotEqual(a, SnapshotId(a.value))
        self.assertNotEqual(a, b)
        self.assertEqual(a, RunId(a.value))


class TestMoney(unittest.TestCase):
    def test_rejects_float(self) -> None:
        with self.assertRaises(TypeError):
            Money(0.1, Currency.USD)  # type: ignore[arg-type]

    def test_cross_currency_arithmetic_forbidden(self) -> None:
        with self.assertRaises(CurrencyMismatchError):
            _ = Money(Decimal("10"), Currency.USD) + Money(Decimal("10"), Currency.VND)


class TestValueObjects(unittest.TestCase):
    def test_probability_range_enforced(self) -> None:
        with self.assertRaises(ValueError):
            Probability(Decimal("1.2"))

    def test_confidence_range_enforced(self) -> None:
        with self.assertRaises(ValueError):
            Confidence(Decimal("-0.1"))

    def test_distribution_must_sum_to_one(self) -> None:
        with self.assertRaises(DistributionError):
            ProbabilityDistribution(
                {"A": Probability(Decimal("0.5")), "B": Probability(Decimal("0.3"))}
            )

    def test_percentage_and_position_size_non_negative(self) -> None:
        with self.assertRaises(ValueError):
            Percentage(Decimal("-1"))
        with self.assertRaises(ValueError):
            PositionSize(Decimal("-0.1"))

    def test_time_range_ordering(self) -> None:
        now = datetime.now(timezone.utc)
        with self.assertRaises(ValueError):
            TimeRange(start=now, end=now - timedelta(days=1))

    def test_value_objects_are_immutable(self) -> None:
        p = Probability(Decimal("0.5"))
        with self.assertRaises(dataclasses.FrozenInstanceError):
            p.value = Decimal("0.9")  # type: ignore[misc]


class TestDecisionLifecycle(unittest.TestCase):
    def test_new_decision_is_draft_and_emits_created(self) -> None:
        d = draft_decision()
        self.assertIs(d.status, DecisionStatus.DRAFT)
        events = d.pull_events()
        self.assertTrue(any(isinstance(e, DecisionCreated) for e in events))

    def test_draft_cannot_be_archived_directly(self) -> None:
        with self.assertRaises(InvalidDecisionTransition):
            draft_decision().archive()

    def test_approval_requires_evidence(self) -> None:
        d = draft_decision()
        d.submit_for_review()
        with self.assertRaises(DecisionError):
            d.approve()

    def test_approval_requires_counter_evidence(self) -> None:
        d = draft_decision()
        d.add_evidence(evidence())
        d.attach_risk_assessment(risk_assessment())
        d.invalidation_conditions = ("thesis breaks if margin collapses",)
        d.submit_for_review()
        with self.assertRaises(DecisionError):
            d.approve()

    def test_approval_requires_risk_assessment(self) -> None:
        d = draft_decision()
        d.add_evidence(evidence())
        d.add_counter_evidence(evidence("bear case"))
        d.invalidation_conditions = ("invalidated on guidance cut",)
        d.submit_for_review()
        with self.assertRaises(DecisionError):
            d.approve()

    def test_full_lifecycle(self) -> None:
        d = draft_decision()
        d.add_evidence(evidence())
        d.add_counter_evidence(evidence("bear case"))
        d.attach_risk_assessment(risk_assessment())
        d.invalidation_conditions = ("invalidated on guidance cut",)
        d.submit_for_review()
        d.approve(note="ok")
        self.assertIs(d.status, DecisionStatus.APPROVED)
        d.archive()
        self.assertIs(d.status, DecisionStatus.ARCHIVED)
        outcomes = [r.outcome for r in d.review_history]
        self.assertEqual(
            outcomes,
            [DecisionStatus.UNDER_REVIEW, DecisionStatus.APPROVED, DecisionStatus.ARCHIVED],
        )
        events = d.pull_events()
        self.assertTrue(any(isinstance(e, EvidenceAdded) for e in events))
        self.assertTrue(any(isinstance(e, DecisionReviewed) for e in events))
        self.assertEqual(d.pull_events(), ())

    def test_rejected_decision_can_only_be_archived(self) -> None:
        d = draft_decision()
        d.submit_for_review()
        d.reject(note="insufficient evidence")
        with self.assertRaises(InvalidDecisionTransition):
            d.submit_for_review()
        d.archive()

    def test_archived_decision_is_immutable(self) -> None:
        d = draft_decision()
        d.submit_for_review()
        d.reject()
        d.archive()
        with self.assertRaises(DecisionError):
            d.add_evidence(evidence())


class TestMarket(unittest.TestCase):
    def test_market_context_carries_regime_and_confidence(self) -> None:
        ctx = MarketContext(
            regime=Regime.EXPANSION,
            confidence=Confidence(Decimal("0.8")),
            liquidity_score=Decimal("0.6"),
            breadth_score=Decimal("0.5"),
            volatility_score=Decimal("0.3"),
            rotation_score=Decimal("0.2"),
            timestamp=datetime.now(timezone.utc),
        )
        self.assertIs(ctx.regime, Regime.EXPANSION)

    def test_canonical_regime_labels(self) -> None:
        self.assertEqual(
            {r.value for r in Regime},
            {"EXPANSION", "RECOVERY", "CONSOLIDATION", "CONTRACTION"},
        )


class TestPortfolio(unittest.TestCase):
    def _position(self, ticker: str, value: str) -> Position:
        return Position(
            ticker=ticker,
            quantity=Decimal("100"),
            average_cost=Money(Decimal("10"), Currency.VND),
            market_value=Money(Decimal(value), Currency.VND),
            unrealized_pnl=Money(Decimal("0"), Currency.VND),
        )

    def _portfolio(self) -> Portfolio:
        return Portfolio(
            owner_id=UserId(),
            cash_balance=Money(Decimal("1000"), Currency.VND),
            positions=(self._position("AAA", "500"),),
        )

    def test_negative_cash_rejected(self) -> None:
        with self.assertRaises(PortfolioError):
            Portfolio(owner_id=UserId(), cash_balance=Money(Decimal("-1"), Currency.VND))

    def test_adjust_cash_cannot_go_negative(self) -> None:
        p = self._portfolio()
        with self.assertRaises(PortfolioError):
            p.adjust_cash(Money(Decimal("-2000"), Currency.VND))

    def test_duplicate_tickers_rejected(self) -> None:
        with self.assertRaises(PortfolioError):
            Portfolio(
                owner_id=UserId(),
                cash_balance=Money(Decimal("0"), Currency.VND),
                positions=(self._position("AAA", "1"), self._position("AAA", "2")),
            )

    def test_allocation_bounded(self) -> None:
        p = self._portfolio()
        self.assertLessEqual(p.allocation, Decimal(1))
        p.upsert_position(self._position("BBB", "300"))
        self.assertEqual(len(p.positions), 2)


class TestRisk(unittest.TestCase):
    def test_risk_report_requires_explanation(self) -> None:
        with self.assertRaises(ValueError):
            RiskReport(
                overall_risk=RiskLevel.HIGH,
                var=Decimal("0.1"),
                cvar=Decimal("0.15"),
                drawdown=Decimal("0.3"),
                liquidity=Decimal("0.5"),
                violations=(),
                recommendations=(),
                explanation="",
            )


class TestBehavior(unittest.TestCase):
    def test_journal_entries_are_immutable(self) -> None:
        entry = DecisionJournalEntry(
            decision_id=DecisionId(),
            original_hypothesis="X outperforms",
            supporting_evidence=("strong FCF",),
            counter_evidence=("rich valuation",),
            expected_outcome="+15% in 12m",
        )
        with self.assertRaises(dataclasses.FrozenInstanceError):
            entry.actual_outcome = "changed"  # type: ignore[misc]

    def test_canonical_bias_catalogue(self) -> None:
        self.assertEqual(len(BiasKind), 8)
        report = BehaviorReport(
            behavior_score=Decimal("0.7"),
            detected_biases=(BiasKind.FOMO, BiasKind.ANCHORING),
            confidence_calibration=Decimal("0.1"),
            recurring_patterns=("chasing recent winners",),
            recommendations=("wait one session before acting",),
            learning_actions=("review last 5 FOMO entries",),
        )
        self.assertIn(BiasKind.FOMO, report.detected_biases)


class TestIdentity(unittest.TestCase):
    def test_user_requires_valid_email(self) -> None:
        with self.assertRaises(ValueError):
            User(email="not-an-email", status="active")


if __name__ == "__main__":
    unittest.main(verbosity=2)
