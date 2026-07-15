"""Position entity (SPEC-03, Entities)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from shared_kernel.money import Money


@dataclass(frozen=True, slots=True)
class Position:
    ticker: str
    quantity: Decimal
    average_cost: Money
    market_value: Money
    unrealized_pnl: Money

    def __post_init__(self) -> None:
        if not self.ticker:
            raise ValueError("position ticker must not be empty")
