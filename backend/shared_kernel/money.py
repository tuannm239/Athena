"""Money and quantity value objects.

Domain rules:
- Money uses Decimal, never float.
- Arithmetic across currencies is forbidden (raises CurrencyMismatchError).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class Currency(StrEnum):
    USD = "USD"
    EUR = "EUR"
    VND = "VND"
    JPY = "JPY"


class CurrencyMismatchError(ValueError):
    """Raised when arithmetic mixes currencies."""


@dataclass(frozen=True, slots=True)
class Money:
    amount: Decimal
    currency: Currency

    def __post_init__(self) -> None:
        if not isinstance(self.amount, Decimal):
            raise TypeError("Money.amount must be Decimal, never float")

    def _check(self, other: "Money") -> None:
        if self.currency is not other.currency:
            raise CurrencyMismatchError(f"{self.currency} vs {other.currency}")

    def __add__(self, other: "Money") -> "Money":
        self._check(other)
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: "Money") -> "Money":
        self._check(other)
        return Money(self.amount - other.amount, self.currency)

    def scaled(self, factor: Decimal) -> "Money":
        return Money(self.amount * factor, self.currency)

    @property
    def is_negative(self) -> bool:
        return self.amount < 0
