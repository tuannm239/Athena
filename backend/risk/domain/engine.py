"""Risk Engine — score composition and assessment builder (RFC-0027 §2/§4).

Risk management always takes precedence over return optimization
(Constitution, Product Principle 2). Every assessment carries a
confidence score; every report carries an explanation.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from risk.domain.metrics import (
    TRADING_DAYS,
    cvar_95,
    days_to_liquidate,
    downside_deviation,
    historical_volatility,
    max_drawdown,
    var_95,
)
from risk.domain.risk_assessment import RiskAssessment, RiskLevel
from risk.domain.risk_report import RiskReport
from shared_kernel.probability import Confidence

_ONE = Decimal(1)
_HUNDRED = Decimal(100)

# RFC-0027 §4 weights and normalization caps.
_CAPS = {
    "volatility": Decimal("0.60"),
    "var": Decimal("0.05"),
    "cvar": Decimal("0.08"),
    "drawdown": Decimal("0.50"),
    "liquidity_days": Decimal(10),
}
_WEIGHTS = {
    "volatility": Decimal("0.25"),
    "var": Decimal("0.25"),
    "cvar": Decimal("0.20"),
    "drawdown": Decimal("0.20"),
    "liquidity_days": Decimal("0.10"),
}


@dataclass(frozen=True, slots=True)
class RiskMetrics:
    volatility: Decimal
    var_95: Decimal
    cvar_95: Decimal
    max_drawdown: Decimal
    downside_deviation: Decimal
    days_to_liquidate: Decimal
    observations: int


def compute_metrics(
    returns: tuple[Decimal, ...],
    *,
    position_value: Decimal,
    average_daily_value: Decimal,
    lookback: int = int(TRADING_DAYS),
) -> RiskMetrics:
    """All RFC-0027 §3 metrics over the last `lookback` observations."""
    window = returns[-lookback:]
    return RiskMetrics(
        volatility=historical_volatility(window),
        var_95=var_95(window),
        cvar_95=cvar_95(window),
        max_drawdown=max_drawdown(window),
        downside_deviation=downside_deviation(window),
        days_to_liquidate=days_to_liquidate(position_value, average_daily_value),
        observations=len(window),
    )


def risk_score(metrics: RiskMetrics) -> Decimal:
    """RFC-0027 §4 weighted, capped composition in 0..100."""

    def capped(value: Decimal, cap: Decimal) -> Decimal:
        return min(value / cap, _ONE)

    return _HUNDRED * (
        _WEIGHTS["volatility"] * capped(metrics.volatility, _CAPS["volatility"])
        + _WEIGHTS["var"] * capped(metrics.var_95, _CAPS["var"])
        + _WEIGHTS["cvar"] * capped(metrics.cvar_95, _CAPS["cvar"])
        + _WEIGHTS["drawdown"] * capped(metrics.max_drawdown, _CAPS["drawdown"])
        + _WEIGHTS["liquidity_days"] * capped(metrics.days_to_liquidate, _CAPS["liquidity_days"])
    )


def level_for(score: Decimal) -> RiskLevel:
    """RFC-0027 §2 bands: 0–20, 21–40, 41–60, 61–80, 81–100."""
    if score <= 20:
        return RiskLevel.VERY_LOW
    if score <= 40:
        return RiskLevel.LOW
    if score <= 60:
        return RiskLevel.MODERATE
    if score <= 80:
        return RiskLevel.HIGH
    return RiskLevel.CRITICAL


def assessment_confidence(observations: int) -> Confidence:
    """min(1, observations/252) — a full lookback gives confidence 1."""
    return Confidence(min(_ONE, Decimal(observations) / TRADING_DAYS))


def build_assessment(metrics: RiskMetrics) -> RiskAssessment:
    score = risk_score(metrics)
    return RiskAssessment(
        var=metrics.var_95,
        cvar=metrics.cvar_95,
        max_drawdown=metrics.max_drawdown,
        stress_score=metrics.downside_deviation,
        liquidity_score=min(metrics.days_to_liquidate / _CAPS["liquidity_days"], _ONE),
        level=level_for(score),
        confidence=assessment_confidence(metrics.observations),
    )


def build_report(
    metrics: RiskMetrics,
    *,
    risk_budget_score: Decimal | None = None,
) -> RiskReport:
    """SPEC-11 output; the risk-budget violation blocks approval upstream."""
    score = risk_score(metrics)
    level = level_for(score)
    violations: tuple[str, ...] = ()
    recommendations: tuple[str, ...] = ()
    if risk_budget_score is not None and score > risk_budget_score:
        violations = (
            f"risk score {score:.2f} exceeds the portfolio risk budget "
            f"{risk_budget_score:.2f} (SPEC-11 rule 2)",
        )
        recommendations = ("reduce position size or hedge before approval",)
    explanation = (
        f"Risk score {score:.2f}/100 ({level.value}) from vol={metrics.volatility:.4f}, "
        f"VaR95={metrics.var_95:.4f}, CVaR95={metrics.cvar_95:.4f}, "
        f"maxDD={metrics.max_drawdown:.4f}, DtL={metrics.days_to_liquidate:.2f}d "
        f"over {metrics.observations} observations (RFC-0027 weights)."
    )
    return RiskReport(
        overall_risk=level,
        var=metrics.var_95,
        cvar=metrics.cvar_95,
        drawdown=metrics.max_drawdown,
        liquidity=metrics.days_to_liquidate,
        violations=violations,
        recommendations=recommendations,
        explanation=explanation,
    )
