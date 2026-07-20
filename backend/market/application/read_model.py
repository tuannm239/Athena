"""Vietnam market snapshot — a read model over persisted price data.

This is the *query* (read) side (CQRS): it projects price observations that
the Data Pipeline has already persisted into the shape the Market page and
dashboard widgets need (indices, breadth, movers, liquidity). It is NOT a
market engine — it contains no regime detection, probability, or business
rules (ALG-001 remains the owner of those); only arithmetic aggregation
over data that already exists.

Boundaries (Clean Architecture / ADR-0003):
  - depends only on the `MarketPriceReader` port (implemented in
    infrastructure over the pipeline's published datasets);
  - never imports a provider, vnstock, SQL, or the pipeline internals;
  - money stays `Decimal` (constitution: never float).

Empty state: when no price data has been synchronised the reader returns
nothing and `snapshot()` yields `MarketSnapshotView.empty()` — the API
serialises that to an explicit empty snapshot (never sample values).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Protocol

from market.domain.vietnam import Index

# Index tickers are stored in the same price dataset as ordinary stocks;
# they are separated here for the "indices" vs "movers/breadth" split.
INDEX_CODES: frozenset[str] = frozenset(index.value for index in Index)

_ZERO = Decimal("0")


@dataclass(frozen=True, slots=True)
class PriceObservation:
    """One persisted daily close for a ticker (from the pipeline)."""

    ticker: str
    day: date
    close: Decimal
    volume: Decimal | None = None


class MarketPriceReader(Protocol):
    """Port: read every persisted daily close (published prices dataset)."""

    def published_prices(self) -> tuple[PriceObservation, ...]: ...


# ---- view DTOs (what the API serialises) ----------------------------------
@dataclass(frozen=True, slots=True)
class IndexQuoteView:
    code: str
    value: Decimal
    change: Decimal
    change_pct: Decimal


@dataclass(frozen=True, slots=True)
class MoverView:
    ticker: str
    price: Decimal
    change_pct: Decimal
    volume: Decimal


@dataclass(frozen=True, slots=True)
class BreadthView:
    advancers: int
    decliners: int
    unchanged: int


@dataclass(frozen=True, slots=True)
class MarketSnapshotView:
    as_of: datetime | None
    indices: tuple[IndexQuoteView, ...]
    breadth: BreadthView
    liquidity_value: Decimal
    top_gainers: tuple[MoverView, ...]
    top_losers: tuple[MoverView, ...]
    top_volume: tuple[MoverView, ...]
    has_data: bool

    @classmethod
    def empty(cls) -> MarketSnapshotView:
        return cls(
            as_of=None,
            indices=(),
            breadth=BreadthView(0, 0, 0),
            liquidity_value=_ZERO,
            top_gainers=(),
            top_losers=(),
            top_volume=(),
            has_data=False,
        )


@dataclass(frozen=True, slots=True)
class _Latest:
    """A ticker's most recent close plus the prior close (for the delta)."""

    ticker: str
    day: date
    close: Decimal
    prev_close: Decimal | None
    volume: Decimal

    @property
    def change(self) -> Decimal:
        return _ZERO if self.prev_close is None else self.close - self.prev_close

    @property
    def change_pct(self) -> Decimal:
        if self.prev_close is None or self.prev_close == _ZERO:
            return _ZERO
        return (self.close - self.prev_close) / self.prev_close

    @property
    def value(self) -> Decimal:
        return self.close * self.volume


@dataclass(frozen=True)
class VnMarketSnapshotQuery:
    """Projects persisted prices into a market snapshot (read-only)."""

    reader: MarketPriceReader
    top_n: int = 5

    def snapshot(self) -> MarketSnapshotView:
        latest = self._latest_per_ticker(self.reader.published_prices())
        if not latest:
            return MarketSnapshotView.empty()

        indices = tuple(
            IndexQuoteView(
                code=item.ticker, value=item.close, change=item.change, change_pct=item.change_pct
            )
            for item in sorted(latest, key=lambda i: i.ticker)
            if item.ticker in INDEX_CODES
        )
        stocks = [item for item in latest if item.ticker not in INDEX_CODES]

        advancers = sum(1 for s in stocks if s.change_pct > _ZERO)
        decliners = sum(1 for s in stocks if s.change_pct < _ZERO)
        unchanged = len(stocks) - advancers - decliners
        liquidity = sum((s.value for s in stocks), _ZERO)

        as_of = max((item.day for item in latest), default=None)
        return MarketSnapshotView(
            as_of=datetime(as_of.year, as_of.month, as_of.day) if as_of else None,
            indices=indices,
            breadth=BreadthView(advancers, decliners, unchanged),
            liquidity_value=liquidity,
            top_gainers=self._movers(stocks, key=lambda s: s.change_pct, reverse=True),
            top_losers=self._movers(stocks, key=lambda s: s.change_pct, reverse=False),
            top_volume=self._movers(stocks, key=lambda s: s.volume, reverse=True),
            has_data=True,
        )

    # -- helpers ------------------------------------------------------------
    @staticmethod
    def _latest_per_ticker(rows: tuple[PriceObservation, ...]) -> list[_Latest]:
        by_ticker: dict[str, list[PriceObservation]] = {}
        for row in rows:
            by_ticker.setdefault(row.ticker, []).append(row)
        out: list[_Latest] = []
        for ticker, observations in by_ticker.items():
            ordered = sorted(observations, key=lambda o: o.day)
            last = ordered[-1]
            prev = ordered[-2] if len(ordered) >= 2 else None
            out.append(
                _Latest(
                    ticker=ticker,
                    day=last.day,
                    close=last.close,
                    prev_close=prev.close if prev is not None else None,
                    volume=last.volume if last.volume is not None else _ZERO,
                )
            )
        return out

    def _movers(self, stocks: list[_Latest], *, key, reverse: bool) -> tuple[MoverView, ...]:  # type: ignore[no-untyped-def]
        ordered = sorted(stocks, key=key, reverse=reverse)[: self.top_n]
        return tuple(
            MoverView(ticker=s.ticker, price=s.close, change_pct=s.change_pct, volume=s.volume)
            for s in ordered
        )
