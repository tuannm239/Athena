"""In-process synchronous event bus (ADR-0010, interim until RFC-0022)."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable

from shared_kernel.events import DomainEvent

Subscriber = Callable[[DomainEvent], None]


class InProcessEventBus:
    """Dispatches events synchronously to type-registered subscribers."""

    def __init__(self) -> None:
        self._subscribers: dict[type[DomainEvent], list[Subscriber]] = defaultdict(list)

    def subscribe(self, event_type: type[DomainEvent], handler: Subscriber) -> None:
        self._subscribers[event_type].append(handler)

    def publish(self, events: tuple[DomainEvent, ...]) -> None:
        for event in events:
            for handler in self._subscribers[type(event)]:
                handler(event)
