"""Percentage, TimeRange and PositionSize value objects (SPEC-03).

All value objects are immutable. Percentages and position sizes are
stored as fractions (0.25 == 25%) using Decimal, never float.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class Percentage:
    value: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.value, Decimal):
            raise TypeError("Percentage.value must be Decimal")
        if self.value < 0:
            raise ValueError("Percentage must be non-negative")


@dataclass(frozen=True, slots=True)
class PositionSize:
    """Position size as a fraction of portfolio value."""

    value: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.value, Decimal):
            raise TypeError("PositionSize.value must be Decimal")
        if self.value < 0:
            raise ValueError("PositionSize must be non-negative")


@dataclass(frozen=True, slots=True)
class TimeRange:
    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        if self.start > self.end:
            raise ValueError("TimeRange.start must not be after end")
