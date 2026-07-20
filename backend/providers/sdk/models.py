"""Provider DTOs — the neutral data vocabulary crossing the provider port.

All DTOs are immutable; monetary/numeric values are Decimal, never float.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum


@dataclass(frozen=True, slots=True)
class PriceBar:
    ticker: str
    day: date
    close: Decimal
    open: Decimal | None = None
    high: Decimal | None = None
    low: Decimal | None = None
    volume: Decimal | None = None

    def __post_init__(self) -> None:
        if self.close <= 0:
            raise ValueError(f"{self.ticker} {self.day}: close must be positive")


@dataclass(frozen=True, slots=True)
class FundamentalRecord:
    ticker: str
    period: str  # e.g. "2026Q1", "2025FY"
    metric: str  # e.g. "roe", "revenue"
    value: Decimal


@dataclass(frozen=True, slots=True)
class MacroPoint:
    indicator: str  # e.g. "interest_rate", "cpi"
    day: date
    value: Decimal


@dataclass(frozen=True, slots=True)
class NewsItem:
    external_id: str
    published_at: datetime
    title: str
    body: str
    tickers: tuple[str, ...] = ()
    source: str = ""


class CorporateActionKind(StrEnum):
    DIVIDEND = "DIVIDEND"
    SPLIT = "SPLIT"
    RIGHTS = "RIGHTS"
    MERGER = "MERGER"


@dataclass(frozen=True, slots=True)
class CorporateAction:
    ticker: str
    day: date
    kind: CorporateActionKind
    factor: Decimal  # adjustment factor / dividend amount


@dataclass(frozen=True, slots=True)
class SectorMapping:
    ticker: str
    sector: str
    industry: str
    exchange: str = ""


@dataclass(frozen=True, slots=True)
class EtfHolding:
    etf: str
    ticker: str
    weight: Decimal


@dataclass(frozen=True, slots=True)
class FxRate:
    pair: str  # e.g. "USDVND"
    day: date
    rate: Decimal


@dataclass(frozen=True, slots=True)
class CommodityQuote:
    symbol: str  # e.g. "IRON_ORE"
    day: date
    price: Decimal


@dataclass(frozen=True, slots=True)
class SymbolInfo:
    """One listed security in a symbol-list capability."""

    ticker: str
    name: str
    exchange: str = ""


@dataclass(frozen=True, slots=True)
class CompanyProfile:
    """Descriptive company profile (not a financial fact)."""

    ticker: str
    name: str
    exchange: str = ""
    industry: str = ""
    sector: str = ""
    profile: str = ""  # business description / summary
    website: str = ""


@dataclass(frozen=True, slots=True)
class ProviderStatus:
    """Health snapshot (Module 2 monitoring)."""

    name: str
    healthy: bool
    consecutive_failures: int
    last_success_at: datetime | None
    detail: str = ""
    checked_at: datetime = field(default_factory=datetime.utcnow)
