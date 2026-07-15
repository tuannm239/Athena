"""Market repository interface (SPEC-03, Repository Interfaces)."""

from __future__ import annotations

from abc import ABC, abstractmethod

from market.domain.market_context import MarketContext


class MarketRepository(ABC):
    @abstractmethod
    def save_context(self, context: MarketContext) -> None: ...

    @abstractmethod
    def latest_context(self) -> MarketContext | None: ...
