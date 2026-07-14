"""Portfolio aggregate (SPEC-03, Entities).

Invariants:
- Cash allocation may not become negative (SPEC-10, Business Rules).
- Portfolio allocation must not exceed 100% (SPEC-03, Invariants).
- Position tickers are unique within a portfolio.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from portfolio.domain.constraints import PortfolioConstraints
from portfolio.domain.position import Position
from shared_kernel.exceptions import DomainError
from shared_kernel.identifiers import PortfolioId, UserId
from shared_kernel.money import Money


class PortfolioError(DomainError):
    """Raised when a portfolio invariant is violated."""


@dataclass(eq=False)
class Portfolio:
    owner_id: UserId
    cash_balance: Money
    positions: tuple[Position, ...] = ()
    constraints: PortfolioConstraints = field(default_factory=PortfolioConstraints)
    id: PortfolioId = field(default_factory=PortfolioId)

    def __post_init__(self) -> None:
        self._validate()

    def upsert_position(self, position: Position) -> None:
        others = tuple(p for p in self.positions if p.ticker != position.ticker)
        self.positions = (*others, position)
        self._validate()

    def remove_position(self, ticker: str) -> None:
        self.positions = tuple(p for p in self.positions if p.ticker != ticker)

    def adjust_cash(self, delta: Money) -> None:
        new_balance = self.cash_balance + delta
        if new_balance.is_negative:
            raise PortfolioError("cash allocation may not become negative (SPEC-10)")
        self.cash_balance = new_balance

    @property
    def total_value(self) -> Decimal:
        invested = sum((p.market_value.amount for p in self.positions), Decimal(0))
        return invested + self.cash_balance.amount

    @property
    def allocation(self) -> Decimal:
        """Invested fraction of total value; must not exceed 1 (SPEC-03)."""
        total = self.total_value
        if total <= 0:
            return Decimal(0)
        invested = sum((p.market_value.amount for p in self.positions), Decimal(0))
        return invested / total

    def _validate(self) -> None:
        if self.cash_balance.is_negative:
            raise PortfolioError("cash allocation may not become negative (SPEC-10)")
        tickers = [p.ticker for p in self.positions]
        if len(tickers) != len(set(tickers)):
            raise PortfolioError("position tickers must be unique within a portfolio")
        if self.allocation > 1:
            raise PortfolioError("portfolio allocation must not exceed 100% (SPEC-03)")
