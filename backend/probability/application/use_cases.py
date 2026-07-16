"""Probability use cases — evaluate a stored decision's hypothesis."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from decision_kernel.domain.repository import DecisionRepository
from probability.domain.engine import ProbabilityEngine
from probability.domain.report import ProbabilityReport
from shared_kernel.exceptions import NotFoundError
from shared_kernel.identifiers import DecisionId


@dataclass
class ProbabilityUseCases:
    decisions: DecisionRepository

    def evaluate_decision(
        self,
        decision_id: DecisionId,
        *,
        as_of: datetime | None = None,
        relevance: dict[str, Decimal] | None = None,
    ) -> ProbabilityReport:
        """Bayesian evaluation of a decision using its own prior and evidence.

        The stored `Decision.probability` is treated as the prior
        (RFC-0018 §5); the report is returned for review — the aggregate
        is not mutated here (updating the decision is an explicit,
        reviewed action through the decisions API).
        """
        decision = self.decisions.get(decision_id)
        if decision is None:
            raise NotFoundError(f"decision not found: {decision_id}")
        engine = ProbabilityEngine(relevance=relevance or {})
        return engine.evaluate(
            hypothesis=decision.hypothesis,
            prior=decision.probability,
            evidence=decision.evidence,
            as_of=as_of or datetime.now(timezone.utc),
            expected_return=decision.expected_return,
            expected_drawdown=decision.expected_drawdown,
            assumptions=decision.assumptions,
        )
