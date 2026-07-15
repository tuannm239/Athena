"""Portfolio repository interface (SPEC-03, Repository Interfaces)."""

from __future__ import annotations

from abc import ABC, abstractmethod

from portfolio.domain.portfolio import Portfolio
from shared_kernel.identifiers import PortfolioId


class PortfolioRepository(ABC):
    @abstractmethod
    def save(self, portfolio: Portfolio) -> None: ...

    @abstractmethod
    def get(self, portfolio_id: PortfolioId) -> Portfolio | None: ...
