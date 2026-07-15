"""Portfolio domain events (SPEC-03, Domain Events)."""

from __future__ import annotations

from dataclasses import dataclass

from shared_kernel.events import DomainEvent
from shared_kernel.identifiers import PortfolioId


@dataclass(frozen=True, slots=True)
class PortfolioUpdated(DomainEvent):
    portfolio_id: PortfolioId
