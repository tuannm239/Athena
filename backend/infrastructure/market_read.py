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
