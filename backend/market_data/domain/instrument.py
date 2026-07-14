"""Instrument entity and price value object."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from shared_kernel.identifiers import InstrumentId
from shared_kernel.money import Currency, Money


class AssetClass(StrEnum):
    EQUITY = "EQUITY"
    ETF = "ETF"
    BOND = "BOND"
    CASH = "CASH"


@dataclass(frozen=True, slots=True)
class Instrument:
    id: InstrumentId
    symbol: str
    name: str
    asset_class: AssetClass
    currency: Currency

    def __post_init__(self) -> None:
        if not self.symbol:
            raise ValueError("symbol must not be empty")


@dataclass(frozen=True, slots=True)
class PricePoint:
    instrument_id: InstrumentId
    as_of: datetime
    close: Money

    def __post_init__(self) -> None:
        if self.close.amount <= Decimal(0):
            raise ValueError("price must be positive")
