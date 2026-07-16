"""Decision aggregate — a structured evaluation of an investment hypothesis.

Business rules encoded here (SPEC-03 Invariants, SPEC-04 Business Rules):
- Probability and Confidence are bounded [0, 1] (by their value objects).
- A Decision cannot transition directly from Draft to Archived.
- Approval requires at least one Evidence and a RiskAssessment.
- Counter evidence is mandatory before approval.
- Every decision must define invalidation conditions before approval.
- Decision types are evaluation outcomes, never trading instructions.

This module has no dependency on any LLM gateway (SPEC-00, ADR-0003).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum

from decision_kernel.domain.events import DecisionCreated, DecisionReviewed, EvidenceAdded
from decision_kernel.domain.evidence import Evidence, EvidenceDirection
from risk.domain.risk_assessment import RiskAssessment
from shared_kernel.events import DomainEvent
from shared_kernel.exceptions import DomainError
from shared_kernel.identifiers import DecisionId
from shared_kernel.measures import PositionSize
from shared_kernel.probability import Confidence, Probability


class DecisionError(DomainError):
    """Raised when a decision business rule is violated."""


class InvalidDecisionTransition(DecisionError):
    """Raised on a state transition the lifecycle does not allow."""


class DecisionStatus(StrEnum):
    DRAFT = "DRAFT"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    ARCHIVED = "ARCHIVED"


class DecisionType(StrEnum):
    """Evaluation outcomes, not trading instructions (SPEC-04)."""

    ACCUMULATE = "ACCUMULATE"
    REDUCE = "REDUCE"
    HOLD = "HOLD"
    WATCHLIST = "WATCHLIST"
    REJECT = "REJECT"


_ALLOWED_TRANSITIONS: dict[DecisionStatus, frozenset[DecisionStatus]] = {
    DecisionStatus.DRAFT: frozenset({DecisionStatus.UNDER_REVIEW}),
    DecisionStatus.UNDER_REVIEW: frozenset({DecisionStatus.APPROVED, DecisionStatus.REJECTED}),
    DecisionStatus.APPROVED: frozenset({DecisionStatus.ARCHIVED}),
    DecisionStatus.REJECTED: frozenset({DecisionStatus.ARCHIVED}),
    DecisionStatus.ARCHIVED: frozenset(),
}


@dataclass(frozen=True, slots=True)
class ReviewRecord:
    """One entry of the decision's review history (SPEC-03, Relations)."""

    outcome: DecisionStatus
    at: datetime
    note: str = ""


@dataclass(eq=False)
class Decision:
    hypothesis: str
    probability: Probability
    confidence: Confidence
    id: DecisionId = field(default_factory=DecisionId)
    decision_type: DecisionType | None = None
    expected_return: Decimal | None = None
    expected_drawdown: Decimal | None = None
    expected_utility: Decimal | None = None
    position_size: PositionSize | None = None
    portfolio_impact: str | None = None
    assumptions: tuple[str, ...] = ()
    invalidation_conditions: tuple[str, ...] = ()
    explanation: str | None = None
    status: DecisionStatus = DecisionStatus.DRAFT
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    evidence: tuple[Evidence, ...] = ()
    risk_assessment: RiskAssessment | None = None
    review_history: tuple[ReviewRecord, ...] = ()
    _events: list[DomainEvent] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        if not self.hypothesis:
            raise DecisionError("decision requires a hypothesis")
        self._events.append(DecisionCreated(decision_id=self.id))

    # -- evidence (ADR-0006: single collection, explicit direction) ---------

    def add_evidence(self, item: Evidence) -> None:
        self._mutable_guard()
        self.evidence = (*self.evidence, item)
        self._events.append(EvidenceAdded(decision_id=self.id, evidence_id=item.id))

    @property
    def supporting_evidence(self) -> tuple[Evidence, ...]:
        return tuple(e for e in self.evidence if e.direction is EvidenceDirection.SUPPORTING)

    @property
    def contradicting_evidence(self) -> tuple[Evidence, ...]:
        return tuple(e for e in self.evidence if e.direction is EvidenceDirection.CONTRADICTING)

    def attach_risk_assessment(self, assessment: RiskAssessment) -> None:
        self._mutable_guard()
        self.risk_assessment = assessment

    # -- lifecycle ----------------------------------------------------------

    def submit_for_review(self) -> None:
        self._transition(DecisionStatus.UNDER_REVIEW)

    def approve(self, note: str = "") -> None:
        if not self.supporting_evidence:
            raise DecisionError("no decision without evidence (SPEC-04)")
        if not self.contradicting_evidence:
            raise DecisionError("counter evidence is mandatory (SPEC-04, ADR-0006)")
        if self.risk_assessment is None:
            raise DecisionError("every approved decision requires a risk assessment (SPEC-03)")
        if not self.invalidation_conditions:
            raise DecisionError("every decision must define invalidation conditions (SPEC-04)")
        self._transition(DecisionStatus.APPROVED, note)

    def reject(self, note: str = "") -> None:
        self._transition(DecisionStatus.REJECTED, note)

    def archive(self) -> None:
        self._transition(DecisionStatus.ARCHIVED)

    # -- events -------------------------------------------------------------

    def pull_events(self) -> tuple[DomainEvent, ...]:
        """Drain pending events; the application layer publishes them (SPEC-03)."""
        events = tuple(self._events)
        self._events.clear()
        return events

    # -- internals ----------------------------------------------------------

    def _mutable_guard(self) -> None:
        if self.status is DecisionStatus.ARCHIVED:
            raise DecisionError("archived decisions are immutable")

    def _transition(self, target: DecisionStatus, note: str = "") -> None:
        if target not in _ALLOWED_TRANSITIONS[self.status]:
            raise InvalidDecisionTransition(f"{self.status} -> {target} is not allowed")
        self.status = target
        record = ReviewRecord(outcome=target, at=datetime.now(timezone.utc), note=note)
        self.review_history = (*self.review_history, record)
        if target in (DecisionStatus.APPROVED, DecisionStatus.REJECTED):
            self._events.append(DecisionReviewed(decision_id=self.id, outcome=target.value))
