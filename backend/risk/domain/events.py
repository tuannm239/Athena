"""Risk domain events (SPEC-03, Domain Events)."""

from __future__ import annotations

from dataclasses import dataclass

from shared_kernel.events import DomainEvent
from shared_kernel.identifiers import DecisionId, PortfolioId


@dataclass(frozen=True, slots=True)
class RiskCalculated(DomainEvent):
    decision_id: DecisionId | None = None
    portfolio_id: PortfolioId | None = None
