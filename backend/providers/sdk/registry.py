"""Configuration-driven provider selection (Phase 2, Module 1).

Connectors register factories under (capability, provider name); the
active provider per capability comes from configuration — no code
changes to swap vendors, every integration stays replaceable.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from enum import StrEnum

from shared_kernel.exceptions import DomainError


class ProviderError(DomainError):
    """Unknown capability/provider or misconfiguration."""


class Capability(StrEnum):
    PRICE = "price"
    FUNDAMENTAL = "fundamental"
    MACRO = "macro"
    NEWS = "news"
    CORPORATE_ACTION = "corporate_action"
    CALENDAR = "calendar"
    SECTOR = "sector"
    ETF = "etf"
    FX = "fx"
    COMMODITY = "commodity"


Factory = Callable[[], object]


@dataclass
class ProviderRegistry:
    """Factories keyed by (capability, name); selection by configuration."""

    _factories: dict[tuple[Capability, str], Factory] = field(default_factory=dict)

    def register(self, capability: Capability, name: str, factory: Factory) -> None:
        key = (capability, name)
        if key in self._factories:
            raise ProviderError(f"provider already registered: {capability.value}/{name}")
        self._factories[key] = factory

    def names(self, capability: Capability) -> tuple[str, ...]:
        return tuple(sorted(n for (c, n) in self._factories if c is capability))

    def resolve(self, capability: Capability, selection: Mapping[str, str]) -> object:
        """Instantiate the configured provider for a capability."""
        name = selection.get(capability.value)
        if name is None:
            raise ProviderError(f"no provider configured for {capability.value!r}")
        factory = self._factories.get((capability, name))
        if factory is None:
            raise ProviderError(
                f"unknown provider {name!r} for {capability.value!r}; "
                f"registered: {self.names(capability)}"
            )
        return factory()
