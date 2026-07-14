"""Unit tests for domain models (Sprint 1 — domain layer)."""
from __future__ import annotations

import sys
import unittest
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from analysis.domain.assessment import CompanyAssessment
from behavior.domain.override import BiasKind, TriggeredOverride
from decision_kernel.domain.decision import Decision, DecisionIntegrityError
from portfolio.domain.portfolio import TargetPortfolio, WeightError
from regime.domain.regime import Regime, RegimeAssessment
from risk.domain.risk_report import Exposure, RiskReport
from shared_kernel.identifiers import DecisionId, InstrumentId, RunId, SnapshotId
from shared_kernel.lineage import Lineage
from shared_kernel.money import Currency, CurrencyMismatchError, Money
from shared_kernel.probability import (
    DistributionError,
    Probability,
    ProbabilityDistribution,
)


def lineage() -> Lineage:
    return Lineage(run_id=RunId(), snapshot_id=SnapshotId())


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
        usd = Money(Decimal("10"), Currency.USD)
        vnd = Money(Decimal("10"), Currency.VND)
        with self.assertRaises(CurrencyMismatchError):
            _ = usd + vnd

    def test_addition(self) -> None:
        a = Money(Decimal("1.50"), Currency.USD)
        b = Money(Decimal("2.50"), Currency.USD)
        self.assertEqual((a + b).amount, Decimal("4.00"))


class TestProbability(unittest.TestCase):
    def test_range_enforced(self) -> None:
        with self.assertRaises(ValueError):
            Probability(Decimal("1.2"))

    def test_distribution_must_sum_to_one(self) -> None:
        with self.assertRaises(DistributionError):
            ProbabilityDistribution(
                {"A": Probability(Decimal("0.5")), "B": Probability(Decimal("0.3"))}
            )

    def test_mode(self) -> None:
        d = ProbabilityDistribution(
            {"A": Probability(Decimal("0.7")), "B": Probability(Decimal("0.3"))}
        )
        self.assertEqual(d.mode(), "A")


class TestRegime(unittest.TestCase):
    def test_rejects_unknown_labels(self) -> None:
        d = ProbabilityDistribution({"MOON": Probability(Decimal("1"))})
        with self.assertRaises(ValueError):
            RegimeAssessment(distribution=d, lineage=lineage())

    def test_dominant(self) -> None:
        d = ProbabilityDistribution(
            {
                Regime.RISK_ON.value: Probability(Decimal("0.8")),
                Regime.RISK_OFF.value: Probability(Decimal("0.2")),
            }
        )
        self.assertIs(RegimeAssessment(d, lineage()).dominant, Regime.RISK_ON)


class TestAssessmentExplainability(unittest.TestCase):
    def test_assessment_without_drivers_is_invalid(self) -> None:
        with self.assertRaises(ValueError):
            CompanyAssessment(
                instrument_id=InstrumentId(),
                outperformance_probability=Probability(Decimal("0.6")),
                drivers=(),
                lineage=lineage(),
            )


class TestPortfolio(unittest.TestCase):
    def test_weights_must_sum_to_one(self) -> None:
        with self.assertRaises(WeightError):
            TargetPortfolio({InstrumentId(): Decimal("0.5")}, lineage())

    def test_negative_weight_rejected(self) -> None:
        with self.assertRaises(WeightError):
            TargetPortfolio(
                {InstrumentId(): Decimal("1.5"), InstrumentId(): Decimal("-0.5")},
                lineage(),
            )


class TestDecisionKernel(unittest.TestCase):
    def _risk(self, lin: Lineage) -> RiskReport:
        return RiskReport(
            exposures=(Exposure("sector:tech", Decimal("0.4")),),
            max_drawdown_estimate=Decimal("0.25"),
            concentration_flag=False,
            lineage=lin,
        )

    def test_decision_requires_consistent_lineage(self) -> None:
        lin_a, lin_b = lineage(), lineage()
        target = TargetPortfolio({InstrumentId(): Decimal("1")}, lin_a)
        with self.assertRaises(DecisionIntegrityError):
            Decision(
                id=DecisionId(),
                target=target,
                risk_report=self._risk(lin_b),
                overrides=(),
                lineage=lin_a,
            )

    def test_valid_decision(self) -> None:
        lin = lineage()
        d = Decision(
            id=DecisionId(),
            target=TargetPortfolio({InstrumentId(): Decimal("1")}, lin),
            risk_report=self._risk(lin),
            overrides=(
                TriggeredOverride(BiasKind.RECENCY, "R-001", "recent-gain chasing damped"),
            ),
            lineage=lin,
        )
        self.assertEqual(len(d.overrides), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
