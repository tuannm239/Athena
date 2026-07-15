"""Portfolio repository interface (SPEC-03, Repository Interfaces)."""

from __future__ import annotations

from abc import ABC, abstractmethod

from portfolio.domain.portfolio import Portfolio
from shared_kernel.identifiers import PortfolioId, UserId


class PortfolioRepository(ABC):
    @abstractmethod
    def save(self, portfolio: Portfolio) -> None: ...

    @abstractmethod
    def get(self, portfolio_id: PortfolioId) -> Portfolio | None: ...

    @abstractmethod
    def list_by_owner(self, owner_id: UserId, *, limit: int, offset: int) -> tuple[Portfolio, ...]:
        """Owner's portfolios, newest first (SPEC-08 §Portfolios)."""

    @abstractmethod
    def count_by_owner(self, owner_id: UserId) -> int: ...
