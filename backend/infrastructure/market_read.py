"""Adapter: read persisted prices for the market read model.

Implements the market `MarketPriceReader` port by consuming the Data
Pipeline's *published* prices dataset — read-only. It does not modify the
pipeline or the provider; it only reads what a sync has already stored
(`DataPipelineUseCases.read_published`). When nothing has been synced yet
the pipeline raises `NotFoundError`, which maps to an empty result so the
API can return an honest empty state (never sample values).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from data_pipeline.application.sync import PRICES_DATASET
from data_pipeline.application.use_cases import DataPipelineUseCases
from market.application.read_model import PriceObservation
from shared_kernel.exceptions import NotFoundError


def _decimal(value: object) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _opt_float(value: object) -> float | None:
    parsed = _decimal(value)
    return None if parsed is None else float(parsed)


@dataclass(frozen=True)
class PublishedMarketPriceReader:
    """Reads the latest published `prices` dataset from the pipeline."""

    pipeline: DataPipelineUseCases

    def published_prices(self) -> tuple[PriceObservation, ...]:
        try:
            frame = self.pipeline.read_published(PRICES_DATASET)
        except NotFoundError:
            return ()  # no sync has published prices yet → empty state
        out: list[PriceObservation] = []
        for row in frame.iter_rows(named=True):
            close = _decimal(row.get("close"))
            day = row.get("day")
            ticker = row.get("ticker")
            if close is None or close <= 0 or day is None or not ticker:
                continue
            out.append(
                PriceObservation(
                    ticker=str(ticker),
                    day=day.date() if hasattr(day, "date") else day,
                    close=close,
                    volume=_decimal(row.get("volume")),
                )
            )
        return tuple(out)

    def ohlc_for(self, ticker: str) -> list[dict[str, object]]:
        """A ticker's persisted daily OHLC bars (for candlestick charts).

        Reads the published prices frame and returns ``[{day, open, high, low,
        close, volume}]`` sorted ascending. ``open``/``high``/``low`` may be
        ``None`` on older snapshots that stored close only; ``close`` is always
        present. Empty list when nothing is synced (honest empty, never sample).
        """
        key = ticker.upper()
        try:
            frame = self.pipeline.read_published(PRICES_DATASET)
        except NotFoundError:
            return []
        bars: list[dict[str, object]] = []
        for row in frame.iter_rows(named=True):
            if str(row.get("ticker") or "").upper() != key:
                continue
            close = _decimal(row.get("close"))
            day = row.get("day")
            if close is None or close <= 0 or day is None:
                continue
            bars.append(
                {
                    "day": (day.date() if hasattr(day, "date") else day).isoformat(),
                    "open": _opt_float(row.get("open")),
                    "high": _opt_float(row.get("high")),
                    "low": _opt_float(row.get("low")),
                    "close": float(close),
                    "volume": _opt_float(row.get("volume")),
                }
            )
        bars.sort(key=lambda b: str(b["day"]))
        return bars
