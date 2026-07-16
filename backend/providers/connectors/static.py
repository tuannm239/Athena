"""Static in-memory provider (Phase 2, Module 2).

A complete, deterministic implementation of every capability port,
loaded from fixtures — used for tests, development and dry runs.
Adapters only: no business logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime

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


@dataclass(frozen=True)
class StaticProvider:
    """Implements all ten provider ports over in-memory fixtures."""

    bars: tuple[PriceBar, ...] = ()
    fundamental_records: tuple[FundamentalRecord, ...] = ()
    macro_points: tuple[MacroPoint, ...] = ()
    news_items: tuple[NewsItem, ...] = ()
    corporate_actions: tuple[CorporateAction, ...] = ()
    calendar: tuple[date, ...] = ()
    sectors: tuple[SectorMapping, ...] = ()
    etf_holdings: tuple[EtfHolding, ...] = ()
    fx_rates: tuple[FxRate, ...] = ()
    commodity_quotes: tuple[CommodityQuote, ...] = field(default=())

    def daily_bars(self, ticker: str, start: date, end: date) -> tuple[PriceBar, ...]:
        return tuple(
            sorted(
                (b for b in self.bars if b.ticker == ticker and start <= b.day <= end),
                key=lambda b: b.day,
            )
        )

    def fundamentals(self, ticker: str, as_of: date) -> tuple[FundamentalRecord, ...]:
        del as_of
        return tuple(r for r in self.fundamental_records if r.ticker == ticker)

    def series(self, indicator: str, start: date, end: date) -> tuple[MacroPoint, ...]:
        return tuple(
            sorted(
                (
                    p
                    for p in self.macro_points
                    if p.indicator == indicator and start <= p.day <= end
                ),
                key=lambda p: p.day,
            )
        )

    def news(self, ticker: str, since: datetime) -> tuple[NewsItem, ...]:
        return tuple(
            sorted(
                (n for n in self.news_items if ticker in n.tickers and n.published_at >= since),
                key=lambda n: n.published_at,
            )
        )

    def actions(self, ticker: str, start: date, end: date) -> tuple[CorporateAction, ...]:
        return tuple(
            a for a in self.corporate_actions if a.ticker == ticker and start <= a.day <= end
        )

    def trading_days(self, start: date, end: date) -> tuple[date, ...]:
        return tuple(d for d in self.calendar if start <= d <= end)

    def classification(self, ticker: str) -> SectorMapping | None:
        for mapping in self.sectors:
            if mapping.ticker == ticker:
                return mapping
        return None

    def holdings(self, etf: str) -> tuple[EtfHolding, ...]:
        return tuple(h for h in self.etf_holdings if h.etf == etf)

    def rate(self, pair: str, day: date) -> FxRate | None:
        candidates = [r for r in self.fx_rates if r.pair == pair and r.day <= day]
        return max(candidates, key=lambda r: r.day) if candidates else None

    def quote(self, symbol: str, day: date) -> CommodityQuote | None:
        candidates = [q for q in self.commodity_quotes if q.symbol == symbol and q.day <= day]
        return max(candidates, key=lambda q: q.day) if candidates else None
