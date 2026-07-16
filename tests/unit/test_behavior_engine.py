"""Unit tests — Behavior Engine ALG-014 (SPEC-12; ADR-0014)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from behavior.domain.bias import BiasKind
from behavior.domain.engine import (
    BehaviorInputError,
    BehaviorThresholds,
    ClosedDecision,
    analyze,
    brier_score,
    calibration_error,
    compute_kpis,
)


def record(
    *,
    probability: str = "0.6",
    confidence: str = "0.6",
    succeeded: bool = True,
    holding: str = "30",
    supporting: int = 2,
    contradicting: int = 1,
    reviewed: bool = True,
) -> ClosedDecision:
    return ClosedDecision(
        stated_probability=Decimal(probability),
        stated_confidence=Decimal(confidence),
        succeeded=succeeded,
        holding_days=Decimal(holding),
        supporting_count=supporting,
        contradicting_count=contradicting,
        reviewed=reviewed,
    )


class TestCalibration:
    def test_perfect_calibration(self) -> None:
        records = (
            record(probability="1", succeeded=True),
            record(probability="0", succeeded=False),
        )
        assert calibration_error(records) == Decimal(0)
        assert brier_score(records) == Decimal(0)

    def test_calibration_error_formula(self) -> None:
        records = (record(probability="0.7", succeeded=False),)
        assert calibration_error(records) == Decimal("0.7")
        assert brier_score(records) == Decimal("0.49")


class TestDetectors:
    def test_overconfidence_detected(self) -> None:
        records = tuple(
            record(confidence="0.9", succeeded=(i == 0)) for i in range(4)
        )  # hit rate 0.25, confidence 0.9
        report = analyze(records)
        assert BiasKind.OVERCONFIDENCE in report.detected_biases
        assert any("confidence" in r for r in report.recommendations)

    def test_confirmation_bias_detected(self) -> None:
        records = tuple(record(supporting=9, contradicting=0) for _ in range(3))
        report = analyze(records)
        assert BiasKind.CONFIRMATION_BIAS in report.detected_biases

    def test_disposition_effect_detected(self) -> None:
        records = (
            record(succeeded=True, holding="5"),
            record(succeeded=True, holding="5", probability="0.9", confidence="0.5"),
            record(succeeded=False, holding="100", probability="0.2", confidence="0.5"),
            record(succeeded=False, holding="90", probability="0.2", confidence="0.5"),
        )
        report = analyze(records)
        assert BiasKind.DISPOSITION_EFFECT in report.detected_biases

    def test_clean_history_detects_nothing(self) -> None:
        records = (
            record(probability="0.6", confidence="0.6", succeeded=True, holding="40"),
            record(probability="0.4", confidence="0.5", succeeded=False, holding="35"),
            record(probability="0.7", confidence="0.6", succeeded=True, holding="45"),
        )
        report = analyze(records)
        assert report.detected_biases == ()
        assert report.behavior_score > Decimal("0.5")
        assert report.recommendations  # advisory guidance always present

    def test_thresholds_configurable(self) -> None:
        records = tuple(record(supporting=3, contradicting=1) for _ in range(3))  # share 0.75
        default = analyze(records)
        strict = analyze(records, BehaviorThresholds(confirmation_share=Decimal("0.7")))
        assert BiasKind.CONFIRMATION_BIAS not in default.detected_biases
        assert BiasKind.CONFIRMATION_BIAS in strict.detected_biases

    def test_deterministic(self) -> None:
        records = tuple(record(confidence="0.9", succeeded=False) for _ in range(3))
        assert analyze(records) == analyze(records)

    def test_empty_history_rejected(self) -> None:
        with pytest.raises(BehaviorInputError):
            analyze(())

    def test_input_validation(self) -> None:
        with pytest.raises(BehaviorInputError):
            record(probability="1.5")


class TestKpis:
    def test_kpis(self) -> None:
        records = (
            record(succeeded=True, holding="10", reviewed=True),
            record(succeeded=True, holding="90", reviewed=False),
            record(succeeded=False, holding="50", reviewed=True),
        )
        kpis = compute_kpis(records)
        assert kpis.average_holding_days == Decimal(50)
        assert kpis.premature_exit_rate == Decimal(1) / Decimal(2)
        assert kpis.review_completion_rate == Decimal(2) / Decimal(3)
