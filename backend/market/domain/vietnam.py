"""Vietnamese market reference data (Phase 7, WS1).

Static, VN-specific reference for the market bounded context: the three
exchanges (HOSE, HNX, UPCoM), the headline indices (VNINDEX, VN30, HNX30, …),
the sector taxonomy, corporate-action types, and a trading-calendar helper
(weekends + configurable public holidays, plus the VN session clock).

Pure domain data — no infrastructure, no I/O. Amounts/limits are Decimal.
Lunar-calendar holidays (Tết, Hùng Kings) shift each year and must be supplied
per year via `TradingCalendar(holidays=…)`; the fixed-date national holidays
are provided as a convenience.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, time, timedelta
from decimal import Decimal
from enum import StrEnum

from shared_kernel.money import Currency


class Exchange(StrEnum):
    HOSE = "HOSE"  # Ho Chi Minh City Stock Exchange
    HNX = "HNX"  # Hanoi Stock Exchange
    UPCOM = "UPCOM"  # Unlisted Public Company Market


@dataclass(frozen=True, slots=True)
class ExchangeInfo:
    code: Exchange
    name: str
    daily_price_limit: Decimal  # ±band on the reference price
    lot_size: int  # standard board lot (shares)
    currency: Currency = Currency.VND


EXCHANGES: dict[Exchange, ExchangeInfo] = {
    Exchange.HOSE: ExchangeInfo(
        Exchange.HOSE, "Ho Chi Minh City Stock Exchange", Decimal("0.07"), 100
    ),
    Exchange.HNX: ExchangeInfo(Exchange.HNX, "Hanoi Stock Exchange", Decimal("0.10"), 100),
    Exchange.UPCOM: ExchangeInfo(
        Exchange.UPCOM, "Unlisted Public Company Market", Decimal("0.15"), 100
    ),
}


class Index(StrEnum):
    VNINDEX = "VNINDEX"
    VN30 = "VN30"
    HNXINDEX = "HNXINDEX"
    HNX30 = "HNX30"
    UPCOMINDEX = "UPCOMINDEX"


@dataclass(frozen=True, slots=True)
class IndexInfo:
    code: Index
    name: str
    exchange: Exchange
    constituents: int | None  # None = all listed on the exchange


INDICES: dict[Index, IndexInfo] = {
    Index.VNINDEX: IndexInfo(Index.VNINDEX, "VN-Index (all HOSE)", Exchange.HOSE, None),
    Index.VN30: IndexInfo(Index.VN30, "VN30 (30 large-cap, liquid HOSE)", Exchange.HOSE, 30),
    Index.HNXINDEX: IndexInfo(Index.HNXINDEX, "HNX-Index (all HNX)", Exchange.HNX, None),
    Index.HNX30: IndexInfo(Index.HNX30, "HNX30 (30 large-cap, liquid HNX)", Exchange.HNX, 30),
    Index.UPCOMINDEX: IndexInfo(Index.UPCOMINDEX, "UPCoM-Index", Exchange.UPCOM, None),
}


class Sector(StrEnum):
    """ICB-aligned level-1 sectors as used for Vietnamese listings."""

    FINANCIALS = "Financials"
    REAL_ESTATE = "Real Estate"
    INDUSTRIALS = "Industrials"
    CONSUMER_STAPLES = "Consumer Staples"
    CONSUMER_DISCRETIONARY = "Consumer Discretionary"
    MATERIALS = "Materials"
    ENERGY = "Energy"
    UTILITIES = "Utilities"
    HEALTH_CARE = "Health Care"
    INFORMATION_TECHNOLOGY = "Information Technology"
    COMMUNICATION_SERVICES = "Communication Services"


SECTORS: tuple[Sector, ...] = tuple(Sector)


class CorporateActionType(StrEnum):
    CASH_DIVIDEND = "CASH_DIVIDEND"
    STOCK_DIVIDEND = "STOCK_DIVIDEND"  # bonus shares
    RIGHTS_ISSUE = "RIGHTS_ISSUE"
    STOCK_SPLIT = "STOCK_SPLIT"
    AGM = "AGM"  # annual general meeting
    EGM = "EGM"  # extraordinary general meeting
    LISTING = "LISTING"
    DELISTING = "DELISTING"


# VN trading sessions (ATO/continuous/ATC), local time (Asia/Ho_Chi_Minh).
MORNING_OPEN = time(9, 0)
MORNING_CLOSE = time(11, 30)
AFTERNOON_OPEN = time(13, 0)
AFTERNOON_CLOSE = time(15, 0)


def price_limit_band(exchange: Exchange, reference_price: Decimal) -> tuple[Decimal, Decimal]:
    """Daily floor/ceiling for a symbol given its reference price (VND).

    Tick-size rounding is intentionally omitted (venue-specific); this returns
    the raw band from the exchange's daily price limit.
    """
    if reference_price <= 0:
        raise ValueError("reference_price must be positive")
    band = EXCHANGES[exchange].daily_price_limit
    floor = reference_price * (Decimal(1) - band)
    ceiling = reference_price * (Decimal(1) + band)
    return floor, ceiling


# Fixed-date Vietnamese national holidays (month, day). Lunar holidays (Tết,
# Hùng Kings' anniversary) are NOT here — supply them per year.
FIXED_NATIONAL_HOLIDAYS: tuple[tuple[int, int], ...] = (
    (1, 1),  # International New Year's Day
    (4, 30),  # Reunification Day
    (5, 1),  # International Labour Day
    (9, 2),  # National Day
)


@dataclass(frozen=True, slots=True)
class TradingCalendar:
    """Determines Vietnamese trading days: Mon–Fri excluding holidays.

    `holidays` should include the fixed national holidays for the year plus the
    lunar-calendar holidays for that year (Tết cluster, Hùng Kings). Use
    `with_fixed_holidays` to seed the fixed dates.
    """

    holidays: frozenset[date] = field(default_factory=frozenset)

    @classmethod
    def with_fixed_holidays(
        cls, year: int, extra: frozenset[date] = frozenset()
    ) -> "TradingCalendar":
        fixed = {date(year, m, d) for (m, d) in FIXED_NATIONAL_HOLIDAYS}
        return cls(holidays=frozenset(fixed | set(extra)))

    def is_trading_day(self, day: date) -> bool:
        return day.weekday() < 5 and day not in self.holidays

    def next_trading_day(self, day: date) -> date:
        nxt = day + timedelta(days=1)
        while not self.is_trading_day(nxt):
            nxt += timedelta(days=1)
        return nxt

    def previous_trading_day(self, day: date) -> date:
        prev = day - timedelta(days=1)
        while not self.is_trading_day(prev):
            prev -= timedelta(days=1)
        return prev

    def trading_days_between(self, start: date, end: date) -> list[date]:
        """Inclusive list of trading days in [start, end]."""
        out: list[date] = []
        cur = start
        while cur <= end:
            if self.is_trading_day(cur):
                out.append(cur)
            cur += timedelta(days=1)
        return out
