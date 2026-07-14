"""Behavior domain events (SPEC-03, Domain Events)."""
from __future__ import annotations

from dataclasses import dataclass

from behavior.domain.bias import BiasKind
from shared_kernel.events import DomainEvent
from shared_kernel.identifiers import DecisionId


@dataclass(frozen=True, slots=True)
class BehaviorDetected(DomainEvent):
    bias: BiasKind
    decision_id: DecisionId | None = None
