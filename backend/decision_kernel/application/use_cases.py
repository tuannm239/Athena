"""Decision use cases (SPEC-08 §Decisions; SPEC-03 lifecycle).

The `risk_assessment` accepted on update is operator-entered data until
ALG-006 (Risk Engine) produces it; approval invariants still hold.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Mapping

from decision_kernel.domain.decision import Decision, DecisionStatus, DecisionType
from decision_kernel.domain.evidence import Evidence, EvidenceDirection
from decision_kernel.domain.repository import DecisionRepository
from risk.domain.risk_assessment import RiskAssessment
from shared_kernel.exceptions import NotFoundError
from shared_kernel.identifiers import DecisionId
from shared_kernel.ports import EventPublisher
from shared_kernel.probability import Confidence, Probability, Reliability


@dataclass(frozen=True, slots=True)
class EvidenceInput:
    source: str
    category: str
    explanation: str
    reliability: Decimal
    direction: EvidenceDirection
    metadata: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CreateDecisionInput:
    hypothesis: str
    probability: Decimal
    confidence: Decimal
    decision_type: DecisionType | None = None
    expected_return: Decimal | None = None
    expected_drawdown: Decimal | None = None
    assumptions: tuple[str, ...] = ()
    invalidation_conditions: tuple[str, ...] = ()
    evidence: tuple[EvidenceInput, ...] = ()


@dataclass(frozen=True, slots=True)
class UpdateDecisionInput:
    """Partial update; None means "leave unchanged" (SPEC-08 PATCH)."""

    explanation: str | None = None
    assumptions: tuple[str, ...] | None = None
    invalidation_conditions: tuple[str, ...] | None = None
    add_evidence: tuple[EvidenceInput, ...] = ()
    risk_assessment: RiskAssessment | None = None
    status: DecisionStatus | None = None
    review_note: str = ""


@dataclass(frozen=True, slots=True)
class DecisionPage:
    items: tuple[Decision, ...]
    total: int
    limit: int
    offset: int


def _to_evidence(item: EvidenceInput) -> Evidence:
    return Evidence(
        source=item.source,
        category=item.category,
        reliability=Reliability(item.reliability),
        direction=item.direction,
        explanation=item.explanation,
        metadata=item.metadata,
    )


@dataclass
class DecisionUseCases:
    repository: DecisionRepository
    events: EventPublisher
    _transitions: dict[DecisionStatus, str] = field(
        default_factory=lambda: {
            DecisionStatus.UNDER_REVIEW: "submit_for_review",
            DecisionStatus.APPROVED: "approve",
            DecisionStatus.REJECTED: "reject",
            DecisionStatus.ARCHIVED: "archive",
        },
        repr=False,
    )

    def create(self, data: CreateDecisionInput) -> Decision:
        decision = Decision(
            hypothesis=data.hypothesis,
            probability=Probability(data.probability),
            confidence=Confidence(data.confidence),
            decision_type=data.decision_type,
            expected_return=data.expected_return,
            expected_drawdown=data.expected_drawdown,
            assumptions=data.assumptions,
            invalidation_conditions=data.invalidation_conditions,
        )
        for item in data.evidence:
            decision.add_evidence(_to_evidence(item))
        self.repository.save(decision)
        self.events.publish(decision.pull_events())
        return decision

    def get(self, decision_id: DecisionId) -> Decision:
        decision = self.repository.get(decision_id)
        if decision is None:
            raise NotFoundError(f"decision not found: {decision_id}")
        return decision

    def list(
        self, *, limit: int, offset: int, status: DecisionStatus | None = None
    ) -> DecisionPage:
        return DecisionPage(
            items=self.repository.list(limit=limit, offset=offset, status=status),
            total=self.repository.count(status=status),
            limit=limit,
            offset=offset,
        )

    def update(self, decision_id: DecisionId, data: UpdateDecisionInput) -> Decision:
        decision = self.get(decision_id)
        if data.explanation is not None:
            decision.explanation = data.explanation
        if data.assumptions is not None:
            decision.assumptions = data.assumptions
        if data.invalidation_conditions is not None:
            decision.invalidation_conditions = data.invalidation_conditions
        for item in data.add_evidence:
            decision.add_evidence(_to_evidence(item))
        if data.risk_assessment is not None:
            decision.attach_risk_assessment(data.risk_assessment)
        if data.status is not None:
            method = self._transitions.get(data.status)
            if method is None:
                raise ValueError(f"cannot request transition to {data.status}")
            if data.status in (DecisionStatus.APPROVED, DecisionStatus.REJECTED):
                getattr(decision, method)(data.review_note)
            else:
                getattr(decision, method)()
        self.repository.save(decision)
        self.events.publish(decision.pull_events())
        return decision
