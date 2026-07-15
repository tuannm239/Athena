"""Decision domain events (SPEC-03, Domain Events)."""

from __future__ import annotations

from dataclasses import dataclass

from shared_kernel.events import DomainEvent
from shared_kernel.identifiers import DecisionId, EvidenceId


@dataclass(frozen=True, slots=True)
class DecisionCreated(DomainEvent):
    decision_id: DecisionId


@dataclass(frozen=True, slots=True)
class DecisionReviewed(DomainEvent):
    decision_id: DecisionId
    outcome: str


@dataclass(frozen=True, slots=True)
class EvidenceAdded(DomainEvent):
    decision_id: DecisionId
    evidence_id: EvidenceId
