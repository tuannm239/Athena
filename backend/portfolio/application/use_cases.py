"""Portfolio use cases (SPEC-08 §Portfolios)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from portfolio.domain.events import PortfolioUpdated
from portfolio.domain.portfolio import Portfolio
from portfolio.domain.repository import PortfolioRepository
from shared_kernel.events import DomainEvent
from shared_kernel.exceptions import NotFoundError
from shared_kernel.identifiers import PortfolioId, UserId
from shared_kernel.money import Currency, Money
from shared_kernel.ports import EventPublisher


@dataclass(frozen=True, slots=True)
class PortfolioPage:
    items: tuple[Portfolio, ...]
    total: int
    limit: int
    offset: int


@dataclass
class PortfolioUseCases:
    repository: PortfolioRepository
    events: EventPublisher

    def create(self, owner_id: UserId, base_currency: Currency, cash: Decimal) -> Portfolio:
        portfolio = Portfolio(owner_id=owner_id, cash_balance=Money(cash, base_currency))
        self.repository.save(portfolio)
        published: tuple[DomainEvent, ...] = (PortfolioUpdated(portfolio_id=portfolio.id),)
        self.events.publish(published)
        return portfolio

    def get_owned(self, portfolio_id: PortfolioId, owner_id: UserId) -> Portfolio:
        portfolio = self.repository.get(portfolio_id)
        if portfolio is None or portfolio.owner_id != owner_id:
            raise NotFoundError(f"portfolio not found: {portfolio_id}")
        return portfolio

    def list(self, owner_id: UserId, *, limit: int, offset: int) -> PortfolioPage:
        return PortfolioPage(
            items=self.repository.list_by_owner(owner_id, limit=limit, offset=offset),
            total=self.repository.count_by_owner(owner_id),
            limit=limit,
            offset=offset,
        )
