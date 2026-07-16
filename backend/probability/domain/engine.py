"""Deterministic probability pipeline (RFC-0026, refining RFC-0018).

Prior → Evidence Reliability → Evidence Freshness → Evidence Relevance
→ Bayesian Update → Calibration → Expected Utility.

Every function is pure; identical inputs produce identical outputs.
Contradictory evidence is never discarded (RFC-0018 §9). Probability
and Confidence are computed and reported separately.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal

from decision_kernel.domain.evidence import Evidence, EvidenceDirection
from probability.domain.errors import (
    InvalidEvidenceError,
    InvalidPriorError,
    MissingHypothesisError,
)
from probability.domain.report import ProbabilityReport
from shared_kernel.probability import Confidence, Probability

FRESHNESS_HORIZON_DAYS = Decimal(365)
CALIBRATION_VERSION = "identity-v1"

_ZERO = Decimal(0)
_ONE = Decimal(1)


@dataclass(frozen=True, slots=True)
class WeightedEvidence:
    """One evidence item with its pipeline weight components (RFC-0026 §2)."""

    evidence: Evidence
    freshness: Decimal
    relevance: Decimal

    @property
    def weight(self) -> Decimal:
        return self.evidence.reliability.value * self.freshness * self.relevance


def freshness(timestamp: datetime, as_of: datetime) -> Decimal:
    """Linear one-year decay: max(0, 1 − age_days/365) (RFC-0026 §2).

    Naive datetimes are interpreted as UTC (SPEC-07: UTC timestamps).
    """
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    if as_of.tzinfo is None:
        as_of = as_of.replace(tzinfo=timezone.utc)
    age_days = Decimal((as_of - timestamp).days)
    if age_days < 0:
        raise InvalidEvidenceError("evidence timestamp is in the future")
    return max(_ZERO, _ONE - age_days / FRESHNESS_HORIZON_DAYS)


def weigh(
    items: tuple[Evidence, ...],
    as_of: datetime,
    relevance: dict[str, Decimal] | None = None,
) -> tuple[WeightedEvidence, ...]:
    """Attach freshness and relevance weights; relevance defaults to 1."""
    weighted: list[WeightedEvidence] = []
    for item in items:
        rel = (relevance or {}).get(str(item.id), _ONE)
        if not (_ZERO <= rel <= _ONE):
            raise InvalidEvidenceError(f"relevance out of range for {item.id}: {rel}")
        weighted.append(
            WeightedEvidence(
                evidence=item, freshness=freshness(item.timestamp, as_of), relevance=rel
            )
        )
    return tuple(weighted)


def bayesian_update(prior: Probability, weighted: tuple[WeightedEvidence, ...]) -> Probability:
    """Odds-form update with BF = (1+w) / 1 / 1/(1+w) (RFC-0026 §3)."""
    p0 = prior.value
    if not (_ZERO < p0 < _ONE):
        raise InvalidPriorError(f"prior must be in the open interval (0, 1), got {p0}")
    odds = p0 / (_ONE - p0)
    for item in weighted:
        factor = _ONE + item.weight
        if item.evidence.direction is EvidenceDirection.SUPPORTING:
            odds *= factor
        elif item.evidence.direction is EvidenceDirection.CONTRADICTING:
            odds /= factor
    return Probability(odds / (_ONE + odds))


def confidence(weighted: tuple[WeightedEvidence, ...]) -> Confidence:
    """coverage × mean(reliability) × consistency (RFC-0026 §4)."""
    n = len(weighted)
    if n == 0:
        return Confidence(_ZERO)
    coverage = Decimal(n) / Decimal(n + 2)
    mean_reliability = sum((w.evidence.reliability.value for w in weighted), _ZERO) / Decimal(n)
    supporting = sum(
        (w.weight for w in weighted if w.evidence.direction is EvidenceDirection.SUPPORTING),
        _ZERO,
    )
    contradicting = sum(
        (w.weight for w in weighted if w.evidence.direction is EvidenceDirection.CONTRADICTING),
        _ZERO,
    )
    directional = supporting + contradicting
    consistency = max(supporting, contradicting) / directional if directional > 0 else _ZERO
    return Confidence(coverage * mean_reliability * consistency)


def expected_utility(
    posterior: Probability,
    expected_return: Decimal | None,
    expected_drawdown: Decimal | None,
) -> Decimal | None:
    """EU = p·return − (1−p)·drawdown (RFC-0026 §6); None when inputs absent."""
    if expected_return is None or expected_drawdown is None:
        return None
    p = posterior.value
    return p * expected_return - (_ONE - p) * expected_drawdown


@dataclass(frozen=True)
class ProbabilityEngine:
    """RFC-0026 pipeline as a deterministic domain service."""

    relevance: dict[str, Decimal] = field(default_factory=dict)

    def evaluate(
        self,
        *,
        hypothesis: str,
        prior: Probability,
        evidence: tuple[Evidence, ...],
        as_of: datetime,
        expected_return: Decimal | None = None,
        expected_drawdown: Decimal | None = None,
        assumptions: tuple[str, ...] = (),
    ) -> ProbabilityReport:
        if not hypothesis:
            raise MissingHypothesisError("hypothesis is required (PE003)")
        weighted = weigh(evidence, as_of, self.relevance)
        posterior = bayesian_update(prior, weighted)
        conf = confidence(weighted)
        utility = expected_utility(posterior, expected_return, expected_drawdown)

        summary = tuple(
            f"{w.evidence.direction.value} [{w.evidence.source}] "
            f"w={w.weight:.6f} (r={w.evidence.reliability.value}, "
            f"f={w.freshness:.4f}, rel={w.relevance})"
            for w in weighted
        )
        explanation = (
            f"Prior {prior.value} updated over {len(weighted)} evidence item(s) "
            f"({sum(1 for w in weighted if w.evidence.direction is EvidenceDirection.SUPPORTING)}"
            f" supporting, "
            f"{sum(1 for w in weighted if w.evidence.direction is EvidenceDirection.CONTRADICTING)}"
            f" contradicting) to posterior {posterior.value:.6f}; "
            f"confidence {conf.value:.6f} reported separately (RFC-0026)."
        )
        return ProbabilityReport(
            hypothesis=hypothesis,
            prior=prior,
            posterior=posterior,
            confidence=conf,
            evidence_summary=summary,
            assumptions=assumptions,
            uncertainty=_ONE - conf.value,
            expected_utility=utility,
            calibration=CALIBRATION_VERSION,
            explanation=explanation,
        )
