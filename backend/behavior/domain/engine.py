"""Behavior Engine — ALG-014 (SPEC-12; ADR-0014).

Deterministic bias detection, confidence calibration and behavioral
KPIs over closed decisions. Behavioral feedback is advisory only —
the Behavior Engine never overrides the Decision Kernel.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from behavior.domain.bias import BehaviorReport, BiasKind
from shared_kernel.exceptions import DomainError

_ZERO = Decimal(0)
_ONE = Decimal(1)


class BehaviorInputError(DomainError):
    """Raised when the closed-decision history is unusable."""


@dataclass(frozen=True, slots=True)
class ClosedDecision:
    """One reviewed decision outcome (SPEC-12 §Inputs)."""

    stated_probability: Decimal
    stated_confidence: Decimal
    succeeded: bool
    holding_days: Decimal
    supporting_count: int
    contradicting_count: int
    reviewed: bool

    def __post_init__(self) -> None:
        for name in ("stated_probability", "stated_confidence"):
            value = getattr(self, name)
            if not (_ZERO <= value <= _ONE):
                raise BehaviorInputError(f"{name} must be in [0, 1], got {value}")
        if self.holding_days < 0:
            raise BehaviorInputError("holding_days must be non-negative")


@dataclass(frozen=True, slots=True)
class BehaviorThresholds:
    """ADR-0014 configurable detector parameters."""

    overconfidence_gap: Decimal = Decimal("0.15")
    confirmation_share: Decimal = Decimal("0.80")
    disposition_ratio: Decimal = Decimal("0.5")


@dataclass(frozen=True, slots=True)
class BehaviorKpis:
    """SPEC-12 §Behavioral KPIs (computable subset, ADR-0014)."""

    average_holding_days: Decimal
    premature_exit_rate: Decimal
    review_completion_rate: Decimal


def _mean(values: tuple[Decimal, ...]) -> Decimal:
    return sum(values, _ZERO) / Decimal(len(values))


def calibration_error(records: tuple[ClosedDecision, ...]) -> Decimal:
    """Mean |stated probability − outcome| (SPEC-12 §Confidence Calibration)."""
    return _mean(
        tuple(abs(r.stated_probability - (_ONE if r.succeeded else _ZERO)) for r in records)
    )


def brier_score(records: tuple[ClosedDecision, ...]) -> Decimal:
    return _mean(
        tuple((r.stated_probability - (_ONE if r.succeeded else _ZERO)) ** 2 for r in records)
    )


def compute_kpis(records: tuple[ClosedDecision, ...]) -> BehaviorKpis:
    average = _mean(tuple(r.holding_days for r in records))
    winners = tuple(r for r in records if r.succeeded)
    premature = (
        Decimal(sum(1 for r in winners if r.holding_days < average / 2)) / Decimal(len(winners))
        if winners
        else _ZERO
    )
    reviewed = Decimal(sum(1 for r in records if r.reviewed)) / Decimal(len(records))
    return BehaviorKpis(
        average_holding_days=average,
        premature_exit_rate=premature,
        review_completion_rate=reviewed,
    )


_ADVICE: dict[BiasKind, tuple[str, str]] = {
    BiasKind.OVERCONFIDENCE: (
        "stated confidence exceeds the realized hit rate; shade confidence down",
        "review the last ten approved decisions against realized outcomes",
    ),
    BiasKind.CONFIRMATION_BIAS: (
        "evidence mix is dominated by supporting items; actively source counter evidence",
        "require at least one fresh contradicting evidence item before approval",
    ),
    BiasKind.DISPOSITION_EFFECT: (
        "winners are closed much earlier than losers; revisit exit rules",
        "journal each early exit of a winning decision with the trigger that caused it",
    ),
}


DEFAULT_THRESHOLDS = BehaviorThresholds()


def analyze(
    records: tuple[ClosedDecision, ...],
    thresholds: BehaviorThresholds = DEFAULT_THRESHOLDS,
) -> BehaviorReport:
    """Deterministic behavior report (SPEC-12 §Outputs; ADR-0014 formulas)."""
    if not records:
        raise BehaviorInputError("at least one closed decision is required")

    detected: list[BiasKind] = []
    patterns: list[str] = []

    hit_rate = Decimal(sum(1 for r in records if r.succeeded)) / Decimal(len(records))
    confidence_gap = _mean(tuple(r.stated_confidence for r in records)) - hit_rate
    if confidence_gap > thresholds.overconfidence_gap:
        detected.append(BiasKind.OVERCONFIDENCE)
        patterns.append(
            f"mean confidence exceeds hit rate by {confidence_gap:.4f} "
            f"(threshold {thresholds.overconfidence_gap})"
        )

    shares = tuple(
        Decimal(r.supporting_count) / Decimal(r.supporting_count + r.contradicting_count)
        for r in records
        if r.supporting_count + r.contradicting_count > 0
    )
    if shares:
        supporting_share = _mean(shares)
        if supporting_share > thresholds.confirmation_share:
            detected.append(BiasKind.CONFIRMATION_BIAS)
            patterns.append(
                f"supporting-evidence share {supporting_share:.4f} "
                f"(threshold {thresholds.confirmation_share})"
            )

    winners = tuple(r.holding_days for r in records if r.succeeded)
    losers = tuple(r.holding_days for r in records if not r.succeeded)
    if winners and losers and _mean(losers) > 0:
        ratio = _mean(winners) / _mean(losers)
        if ratio < thresholds.disposition_ratio:
            detected.append(BiasKind.DISPOSITION_EFFECT)
            patterns.append(
                f"winner/loser holding ratio {ratio:.4f} (threshold {thresholds.disposition_ratio})"
            )

    error = calibration_error(records)
    score = max(_ZERO, _ONE - Decimal("0.2") * Decimal(len(detected)) - error)
    recommendations = tuple(_ADVICE[b][0] for b in detected)
    learning = tuple(_ADVICE[b][1] for b in detected)
    return BehaviorReport(
        behavior_score=score,
        detected_biases=tuple(detected),
        confidence_calibration=error,
        recurring_patterns=tuple(patterns),
        recommendations=recommendations
        or ("no bias detected above thresholds; keep journaling every decision",),
        learning_actions=learning or ("maintain review completion above 90%",),
    )
