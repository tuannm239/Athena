"""Decision-pipeline bridge (Phase 2, Module 3).

Adapts published, quality-gated market data to the fact mappings the
DSL evaluator consumes — the same ``(day, ticker) → facts`` signature
the Backtest Engine's ``FactProvider`` and the Decision Kernel's
``facts`` input expect. No provider type crosses this boundary: the
decision pipeline sees only published datasets.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Mapping

from data_pipeline.application.sync import PRICES_DATASET
from data_pipeline.application.use_cases import DataPipelineUseCases
from dsl.domain.evaluator import FactValue


@dataclass(frozen=True)
class PublishedPriceFacts:
    """Point-in-time facts from the latest published price dataset.

    Facts exposed per (day, ticker): ``Company.Ticker``,
    ``Feature.price.close`` / ``Feature.price.volume`` when priced that
    day, and ``Company.Sector`` / ``Company.Industry`` when a
    classification is known. Days without data yield no price facts —
    rules simply do not match (no look-ahead, no interpolation).
    """

    closes: Mapping[tuple[str, date], Decimal]
    volumes: Mapping[tuple[str, date], Decimal]
    classifications: Mapping[str, tuple[str, str]]  # ticker -> (sector, industry)

    @classmethod
    def from_pipeline(
        cls,
        pipeline: DataPipelineUseCases,
        *,
        dataset_id: str = PRICES_DATASET,
        classifications: Mapping[str, tuple[str, str]] | None = None,
    ) -> PublishedPriceFacts:
        frame = pipeline.read_published(dataset_id)
        closes: dict[tuple[str, date], Decimal] = {}
        volumes: dict[tuple[str, date], Decimal] = {}
        for row in frame.iter_rows(named=True):
            day = row["day"]
            if isinstance(day, datetime):
                day = day.date()
            key = (str(row["ticker"]), day)
            closes[key] = Decimal(str(row["close"]))
            if row.get("volume") is not None:
                volumes[key] = Decimal(str(row["volume"]))
        return cls(closes=closes, volumes=volumes, classifications=dict(classifications or {}))

    def __call__(self, day: date, ticker: str) -> Mapping[str, FactValue]:
        facts: dict[str, FactValue] = {"Company.Ticker": ticker}
        close = self.closes.get((ticker, day))
        if close is not None:
            facts["Feature.price.close"] = close
        volume = self.volumes.get((ticker, day))
        if volume is not None:
            facts["Feature.price.volume"] = volume
        known = self.classifications.get(ticker)
        if known is not None:
            facts["Company.Sector"], facts["Company.Industry"] = known
        return facts
