"""Provider ports (Phase 2, Module 1) — one Protocol per capability.

Adapters implement these; consumers (data pipeline, knowledge graph,
engines) depend only on the Protocols and DTOs. Provider selection is
configuration-driven through the ProviderRegistry.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Protocol

from providers.sdk.models import (
    CommodityQuote,
    CorporateAction,
    EtfHolding,
    FundamentalRecord,
    FxRate,
    MacroPoint,
    NewsItem,
    PriceBar,
    SectorMapping,
)


class PriceProvider(Protocol):
    def daily_bars(self, ticker: str, start: date, end: date) -> tuple[PriceBar, ...]: ...


class FundamentalProvider(Protocol):
    def fundamentals(self, ticker: str, as_of: date) -> tuple[FundamentalRecord, ...]: ...


class MacroProvider(Protocol):
    def series(self, indicator: str, start: date, end: date) -> tuple[MacroPoint, ...]: ...


class NewsProvider(Protocol):
    def news(self, ticker: str, since: datetime) -> tuple[NewsItem, ...]: ...


class CorporateActionProvider(Protocol):
    def actions(self, ticker: str, start: date, end: date) -> tuple[CorporateAction, ...]: ...


class CalendarProvider(Protocol):
    def trading_days(self, start: date, end: date) -> tuple[date, ...]: ...


class SectorProvider(Protocol):
    def classification(self, ticker: str) -> SectorMapping | None: ...


class ETFProvider(Protocol):
    def holdings(self, etf: str) -> tuple[EtfHolding, ...]: ...


class FXProvider(Protocol):
    def rate(self, pair: str, day: date) -> FxRate | None: ...


class CommodityProvider(Protocol):
    def quote(self, symbol: str, day: date) -> CommodityQuote | None: ...
