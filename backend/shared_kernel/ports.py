"""Shared application-layer ports (SPEC-02 Hexagonal Architecture).

Ports are framework-free protocols; adapters live in infrastructure.
"""

from __future__ import annotations

from typing import Protocol

from shared_kernel.events import DomainEvent


class EventPublisher(Protocol):
    """Publishes domain events drained from aggregates (SPEC-03; ADR-0010)."""

    def publish(self, events: tuple[DomainEvent, ...]) -> None: ...
