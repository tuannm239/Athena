"""Unit tests — Risk Engine ALG-006 (RFC-0027; SPEC-11)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from risk.domain.engine import (
    RiskMetrics,
    assessment_confidence,
    build_assessment,
    build_report,
    compute_metrics,
    level_for,
    risk_score,
)
from risk.domain.metrics import (
    RiskInputError,
    cvar_95,
    days_to_liquidate,
    historical_volatility,
    max_drawdown,
    var_95,
)
from risk.domain.risk_assessment import RiskLevel


def series(*values: str) -> tuple[Decimal, ...]:
    return tuple(Decimal(v) for v in values)


FIXED = series(
    "0.01",
    "-0.02",
    "0.005",
    "0.015",
    "-0.03",
    "0.02",
    "-0.01",
    "0.0",
    "0.012",
    "-0.008",
    "0.007",
    "-0.015",
    "0.01",
    "0.004",
    "-0.025",
    "0.018",
    "-0.005",
    "0.009",
    "-0.012",
    "0.006",
)


class TestMetrics:
    def test_var_and_cvar_regression(self) -> None:
        assert var_95(FIXED) == Decimal("0.03")
        assert cvar_95(FIXED) == Decimal("0.03")

    def test_cvar_at_least_var(self) -> None:
        wide = FIXED + series("-0.08")
        assert cvar_95(wide) >= var_95(wide)

    def test_max_drawdown_known_path(self) -> None:
        path = series("0.10", "-0.50", "0.20")
        assert max_drawdown(path) == Decimal("0.5")

    def test_zero_variance_series(self) -> None:
        flat = series("0.0", "0.0", "0.0", "0.0")
        assert historical_volatility(flat) == Decimal(0)
        assert var_95(flat) == Decimal(0)
        assert max_drawdown(flat) == Decimal(0)

    def test_days_to_liquidate(self) -> None:
        assert days_to_liquidate(Decimal(1000), Decimal(200)) == Decimal(5)
        with pytest.raises(RiskInputError):
            days_to_liquidate(Decimal(1000), Decimal(0))

    def test_too_short_series_rejected(self) -> None:
        with pytest.raises(RiskInputError):
            var_95(series("0.01"))

    def test_determinism(self) -> None:
        results = {historical_volatility(FIXED) for _ in range(5)}
        assert len(results) == 1


class TestScoreAndLevels:
    @pytest.mark.parametrize(
        ("score", "level"),
        [
            ("0", RiskLevel.VERY_LOW),
            ("20", RiskLevel.VERY_LOW),
            ("20.5", RiskLevel.LOW),
            ("40", RiskLevel.LOW),
            ("60", RiskLevel.MODERATE),
            ("80", RiskLevel.HIGH),
            ("81", RiskLevel.CRITICAL),
            ("100", RiskLevel.CRITICAL),
        ],
    )
    def test_bands(self, score: str, level: RiskLevel) -> None:
        assert level_for(Decimal(score)) is level

    def test_score_bounded_and_monotone_in_risk(self) -> None:
        calm = compute_metrics(
            FIXED, position_value=Decimal(100), average_daily_value=Decimal(1000)
        )
        stressed = compute_metrics(
            FIXED + series("-0.10", "-0.12", "-0.08"),
            position_value=Decimal(100_000),
            average_daily_value=Decimal(1000),
        )
        assert Decimal(0) <= risk_score(calm) <= Decimal(100)
        assert risk_score(stressed) > risk_score(calm)
        assert risk_score(stressed) <= Decimal(100)


class TestAssessmentAndReport:
    def _metrics(self) -> RiskMetrics:
        return compute_metrics(
            FIXED, position_value=Decimal(1000), average_daily_value=Decimal(500)
        )

    def test_assessment_fields(self) -> None:
        assessment = build_assessment(self._metrics())
        assert assessment.var == Decimal("0.03")
        assert Decimal(0) <= assessment.liquidity_score <= Decimal(1)
        assert assessment.confidence.value == assessment_confidence(20).value

    def test_confidence_scales_with_lookback(self) -> None:
        assert assessment_confidence(252).value == Decimal(1)
        assert assessment_confidence(126).value == Decimal(126) / Decimal(252)

    def test_report_explanation_and_budget_violation(self) -> None:
        report = build_report(self._metrics(), risk_budget_score=Decimal(1))
        assert report.explanation
        assert report.violations and "risk budget" in report.violations[0]
        clean = build_report(self._metrics(), risk_budget_score=Decimal(100))
        assert clean.violations == ()
