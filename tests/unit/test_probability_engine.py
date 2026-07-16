"""Unit tests — Probability Engine (RFC-0018, RFC-0026)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from decision_kernel.domain.evidence import Evidence, EvidenceDirection
from probability.domain.engine import (
    ProbabilityEngine,
    bayesian_update,
    confidence,
    expected_utility,
    freshness,
    weigh,
)
from probability.domain.errors import (
    InvalidEvidenceError,
    InvalidPriorError,
    MissingHypothesisError,
)
from shared_kernel.probability import Probability, Reliability

AS_OF = datetime(2026, 7, 16, tzinfo=timezone.utc)


def evidence(
    direction: EvidenceDirection,
    reliability: str = "0.8",
    age_days: int = 30,
    source: str = "unit",
) -> Evidence:
    return Evidence(
        source=source,
        category="fundamental",
        reliability=Reliability(Decimal(reliability)),
        direction=direction,
        explanation="test evidence",
        timestamp=AS_OF - timedelta(days=age_days),
    )


def engine() -> ProbabilityEngine:
    return ProbabilityEngine()


class TestFreshness:
    def test_linear_decay(self) -> None:
        assert freshness(AS_OF, AS_OF) == Decimal(1)
        year_old = freshness(AS_OF - timedelta(days=365), AS_OF)
        assert year_old == Decimal(0)
        half = freshness(AS_OF - timedelta(days=182), AS_OF)
        assert Decimal("0.49") < half < Decimal("0.51")

    def test_future_evidence_rejected(self) -> None:
        with pytest.raises(InvalidEvidenceError):
            freshness(AS_OF + timedelta(days=2), AS_OF)


class TestBayesianUpdate:
    def test_supporting_raises_and_contradicting_lowers(self) -> None:
        prior = Probability(Decimal("0.5"))
        up = bayesian_update(prior, weigh((evidence(EvidenceDirection.SUPPORTING),), AS_OF))
        down = bayesian_update(prior, weigh((evidence(EvidenceDirection.CONTRADICTING),), AS_OF))
        assert up.value > prior.value > down.value

    def test_neutral_evidence_is_a_no_op_on_probability(self) -> None:
        prior = Probability(Decimal("0.5"))
        result = bayesian_update(prior, weigh((evidence(EvidenceDirection.NEUTRAL),), AS_OF))
        assert result.value == prior.value

    def test_posterior_stays_in_open_interval(self) -> None:
        prior = Probability(Decimal("0.99"))
        many = tuple(evidence(EvidenceDirection.SUPPORTING, source=f"s{i}") for i in range(50))
        posterior = bayesian_update(prior, weigh(many, AS_OF))
        assert Decimal(0) < posterior.value < Decimal(1)

    def test_invalid_prior_is_pe001(self) -> None:
        with pytest.raises(InvalidPriorError):
            bayesian_update(Probability(Decimal(1)), ())

    def test_contradictory_evidence_never_discarded(self) -> None:
        prior = Probability(Decimal("0.6"))
        mixed = weigh(
            (
                evidence(EvidenceDirection.SUPPORTING),
                evidence(EvidenceDirection.CONTRADICTING),
            ),
            AS_OF,
        )
        only_support = weigh((evidence(EvidenceDirection.SUPPORTING),), AS_OF)
        assert bayesian_update(prior, mixed).value < bayesian_update(prior, only_support).value

    def test_deterministic(self) -> None:
        prior = Probability(Decimal("0.4"))
        items = weigh(
            (evidence(EvidenceDirection.SUPPORTING), evidence(EvidenceDirection.CONTRADICTING)),
            AS_OF,
        )
        results = {bayesian_update(prior, items).value for _ in range(5)}
        assert len(results) == 1


class TestConfidence:
    def test_no_evidence_means_zero_confidence(self) -> None:
        assert confidence(()).value == Decimal(0)

    def test_more_evidence_raises_confidence(self) -> None:
        one = confidence(weigh((evidence(EvidenceDirection.SUPPORTING),), AS_OF))
        three = confidence(
            weigh(
                tuple(evidence(EvidenceDirection.SUPPORTING, source=f"s{i}") for i in range(3)),
                AS_OF,
            )
        )
        assert three.value > one.value

    def test_relevance_out_of_range_is_pe002(self) -> None:
        item = evidence(EvidenceDirection.SUPPORTING)
        with pytest.raises(InvalidEvidenceError):
            weigh((item,), AS_OF, {str(item.id): Decimal("1.5")})


class TestExpectedUtility:
    def test_formula(self) -> None:
        eu = expected_utility(Probability(Decimal("0.6")), Decimal("0.2"), Decimal("0.1"))
        assert eu == Decimal("0.6") * Decimal("0.2") - Decimal("0.4") * Decimal("0.1")

    def test_none_when_inputs_missing(self) -> None:
        assert expected_utility(Probability(Decimal("0.6")), None, Decimal("0.1")) is None


class TestEngineReport:
    def test_full_report(self) -> None:
        report = engine().evaluate(
            hypothesis="X outperforms",
            prior=Probability(Decimal("0.5")),
            evidence=(
                evidence(EvidenceDirection.SUPPORTING),
                evidence(EvidenceDirection.CONTRADICTING, reliability="0.4"),
            ),
            as_of=AS_OF,
            expected_return=Decimal("0.15"),
            expected_drawdown=Decimal("0.2"),
            assumptions=("margins hold",),
        )
        assert report.posterior.value != report.prior.value
        assert report.uncertainty == Decimal(1) - report.confidence.value
        assert report.calibration == "identity-v1"
        assert len(report.evidence_summary) == 2
        assert report.explanation
        assert report.expected_utility is not None

    def test_missing_hypothesis_is_pe003(self) -> None:
        with pytest.raises(MissingHypothesisError):
            engine().evaluate(
                hypothesis="",
                prior=Probability(Decimal("0.5")),
                evidence=(),
                as_of=AS_OF,
            )

    def test_probability_and_confidence_are_separate(self) -> None:
        report = engine().evaluate(
            hypothesis="X",
            prior=Probability(Decimal("0.5")),
            evidence=(evidence(EvidenceDirection.SUPPORTING),),
            as_of=AS_OF,
        )
        assert report.posterior.value != report.confidence.value
