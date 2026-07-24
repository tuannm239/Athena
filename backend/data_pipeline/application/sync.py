"""Provider → pipeline synchronization (Phase 2, Module 3; RFC-0024 §9).

Bridges the provider SDK to the RFC-0024 pipeline: every sync run is a
complete pipeline execution (ingest → validate → normalize → quality),
so quality gates, lineage and quarantine apply to provider data
unchanged. Conventions are recorded in ADR-0017:

- Dataset versions encode the sync-window end date (``YYYY-MM-DD``);
  the incremental watermark is recovered from the latest *published*
  version, so no separate sync-state store exists and the watermark
  survives restarts and rollbacks for free.
- Replays re-fetch an identical window under version ``{end}#rN``;
  published history is never overwritten (forward-only).
- Numeric provider values are stored as canonical strings so Decimal
  exactness survives snapshot round-trips (floats never enter).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Iterable

import polars as pl

from data_pipeline.application.use_cases import DataPipelineUseCases
from data_pipeline.domain.dataset import DatasetSchema, DatasetStatus, DatasetVersion
from providers.sdk.models import FundamentalRecord, FxRate, MacroPoint, PriceBar
from providers.sdk.ports import (
    FundamentalProvider,
    FXProvider,
    MacroProvider,
    PriceProvider,
)
from shared_kernel.exceptions import DomainError

PRICES_DATASET = "prices"
MACRO_DATASET = "macro"
FUNDAMENTALS_DATASET = "fundamentals"
FX_DATASET = "fx"

PRICE_SCHEMA = DatasetSchema(
    required_columns=("ticker", "day", "close"),
    key_columns=("ticker", "day"),
    timestamp_column="day",
)
MACRO_SCHEMA = DatasetSchema(
    required_columns=("indicator", "day", "value"),
    key_columns=("indicator", "day"),
    timestamp_column="day",
)
FUNDAMENTAL_SCHEMA = DatasetSchema(
    required_columns=("ticker", "period", "metric", "value", "as_of"),
    key_columns=("ticker", "period", "metric"),
    timestamp_column="as_of",
)
FX_SCHEMA = DatasetSchema(
    required_columns=("pair", "day", "rate"),
    key_columns=("pair", "day"),
    timestamp_column="day",
)


class SyncError(DomainError):
    """Sync cannot proceed (no baseline, empty provider window)."""


def _ts(day: date) -> datetime:
    return datetime.combine(day, time.min, tzinfo=timezone.utc)


def _opt(value: object) -> str | None:
    return None if value is None else str(value)


def price_frame(bars: Iterable[PriceBar]) -> pl.DataFrame:
    rows: list[dict[str, object]] = [
        {
            "ticker": bar.ticker,
            "day": _ts(bar.day),
            "open": _opt(bar.open),
            "high": _opt(bar.high),
            "low": _opt(bar.low),
            "close": str(bar.close),
            "volume": _opt(bar.volume),
        }
        for bar in bars
    ]
    return pl.DataFrame(
        rows,
        schema={
            "ticker": pl.Utf8,
            "day": pl.Datetime("us", "UTC"),
            # OHLC persisted so the workspace can render candlesticks; close is
            # the only required column (open/high/low are nullable per bar).
            "open": pl.Utf8,
            "high": pl.Utf8,
            "low": pl.Utf8,
            "close": pl.Utf8,
            "volume": pl.Utf8,
        },
    )


def macro_frame(points: Iterable[MacroPoint]) -> pl.DataFrame:
    rows: list[dict[str, object]] = [
        {"indicator": p.indicator, "day": _ts(p.day), "value": str(p.value)} for p in points
    ]
    return pl.DataFrame(
        rows,
        schema={"indicator": pl.Utf8, "day": pl.Datetime("us", "UTC"), "value": pl.Utf8},
    )


def fundamental_frame(records: Iterable[FundamentalRecord], as_of: date) -> pl.DataFrame:
    rows: list[dict[str, object]] = [
        {
            "ticker": r.ticker,
            "period": r.period,
            "metric": r.metric,
            "value": str(r.value),
            "as_of": _ts(as_of),
        }
        for r in records
    ]
    return pl.DataFrame(
        rows,
        schema={
            "ticker": pl.Utf8,
            "period": pl.Utf8,
            "metric": pl.Utf8,
            "value": pl.Utf8,
            "as_of": pl.Datetime("us", "UTC"),
        },
    )


def fx_frame(rates: Iterable[FxRate]) -> pl.DataFrame:
    rows: list[dict[str, object]] = [
        {"pair": r.pair, "day": _ts(r.day), "rate": str(r.rate)} for r in rates
    ]
    return pl.DataFrame(
        rows,
        schema={"pair": pl.Utf8, "day": pl.Datetime("us", "UTC"), "rate": pl.Utf8},
    )


@dataclass
class ProviderSyncService:
    """Full/incremental/replay synchronization from providers into datasets.

    ``source`` names the upstream for lineage (e.g. ``provider:local``);
    every run lands as an immutable, quality-gated ``DatasetVersion``.
    """

    pipeline: DataPipelineUseCases
    source: str

    # -- prices --------------------------------------------------------------

    def full_sync_prices(
        self,
        provider: PriceProvider,
        tickers: Iterable[str],
        start: date,
        end: date,
        *,
        as_of: datetime | None = None,
    ) -> DatasetVersion:
        bars = self._fetch_bars(provider, tickers, start, end)
        return self._run(PRICES_DATASET, end.isoformat(), price_frame(bars), PRICE_SCHEMA, as_of)

    def incremental_sync_prices(
        self,
        provider: PriceProvider,
        tickers: Iterable[str],
        *,
        as_of: datetime,
        initial_start: date | None = None,
    ) -> DatasetVersion | None:
        window = self._window(PRICES_DATASET, as_of, initial_start)
        if window is None:
            return None
        start, end = window
        bars = self._fetch_bars(provider, tickers, start, end, allow_empty=True)
        if not bars:
            return None
        return self._run(PRICES_DATASET, end.isoformat(), price_frame(bars), PRICE_SCHEMA, as_of)

    def replay_prices(
        self,
        provider: PriceProvider,
        tickers: Iterable[str],
        start: date,
        end: date,
        *,
        as_of: datetime | None = None,
    ) -> DatasetVersion:
        """Re-fetch an already-synced window as a new, comparable version."""
        bars = self._fetch_bars(provider, tickers, start, end)
        version = self._replay_version(PRICES_DATASET, end)
        return self._run(PRICES_DATASET, version, price_frame(bars), PRICE_SCHEMA, as_of)

    # -- macro ----------------------------------------------------------------

    def full_sync_macro(
        self,
        provider: MacroProvider,
        indicators: Iterable[str],
        start: date,
        end: date,
        *,
        as_of: datetime | None = None,
    ) -> DatasetVersion:
        points = self._fetch_points(provider, indicators, start, end)
        return self._run(MACRO_DATASET, end.isoformat(), macro_frame(points), MACRO_SCHEMA, as_of)

    def incremental_sync_macro(
        self,
        provider: MacroProvider,
        indicators: Iterable[str],
        *,
        as_of: datetime,
        initial_start: date | None = None,
    ) -> DatasetVersion | None:
        window = self._window(MACRO_DATASET, as_of, initial_start)
        if window is None:
            return None
        start, end = window
        points = self._fetch_points(provider, indicators, start, end, allow_empty=True)
        if not points:
            return None
        return self._run(MACRO_DATASET, end.isoformat(), macro_frame(points), MACRO_SCHEMA, as_of)

    # -- fundamentals / fx ----------------------------------------------------

    def sync_fundamentals(
        self,
        provider: FundamentalProvider,
        tickers: Iterable[str],
        day: date,
        *,
        as_of: datetime | None = None,
    ) -> DatasetVersion:
        records: list[FundamentalRecord] = []
        for ticker in sorted(set(tickers)):
            records.extend(provider.fundamentals(ticker, day))
        if not records:
            raise SyncError(f"{self.source} returned no fundamentals for {day}")
        frame = fundamental_frame(records, day)
        return self._run(FUNDAMENTALS_DATASET, day.isoformat(), frame, FUNDAMENTAL_SCHEMA, as_of)

    def sync_fx(
        self,
        provider: FXProvider,
        pairs: Iterable[str],
        day: date,
        *,
        as_of: datetime | None = None,
    ) -> DatasetVersion:
        rates = [
            rate for pair in sorted(set(pairs)) if (rate := provider.rate(pair, day)) is not None
        ]
        if not rates:
            raise SyncError(f"{self.source} returned no FX rates for {day}")
        return self._run(FX_DATASET, day.isoformat(), fx_frame(rates), FX_SCHEMA, as_of)

    # -- shared machinery -------------------------------------------------------

    def rollback(self, dataset_id: str, version: str) -> DatasetVersion | None:
        """Retire a published sync run; the previous published version wins."""
        return self.pipeline.rollback_dataset(dataset_id, version)

    def watermark(self, dataset_id: str) -> date | None:
        """Last synced day, recovered from the latest published version."""
        latest = self.pipeline.catalog.latest(dataset_id, status=DatasetStatus.PUBLISHED)
        if latest is None:
            return None
        return date.fromisoformat(latest.version[:10])

    def _window(
        self, dataset_id: str, as_of: datetime, initial_start: date | None
    ) -> tuple[date, date] | None:
        last = self.watermark(dataset_id)
        if last is None:
            if initial_start is None:
                raise SyncError(
                    f"no published baseline for {dataset_id}; "
                    "run a full sync first or pass initial_start"
                )
            start = initial_start
        else:
            start = last + timedelta(days=1)
        end = as_of.date()
        if start > end:
            return None
        return start, end

    def _fetch_bars(
        self,
        provider: PriceProvider,
        tickers: Iterable[str],
        start: date,
        end: date,
        *,
        allow_empty: bool = False,
    ) -> tuple[PriceBar, ...]:
        bars: list[PriceBar] = []
        for ticker in sorted(set(tickers)):
            bars.extend(provider.daily_bars(ticker, start, end))
        if not bars and not allow_empty:
            raise SyncError(f"{self.source} returned no bars for {start}..{end}")
        return tuple(bars)

    def _fetch_points(
        self,
        provider: MacroProvider,
        indicators: Iterable[str],
        start: date,
        end: date,
        *,
        allow_empty: bool = False,
    ) -> tuple[MacroPoint, ...]:
        points: list[MacroPoint] = []
        for indicator in sorted(set(indicators)):
            points.extend(provider.series(indicator, start, end))
        if not points and not allow_empty:
            raise SyncError(f"{self.source} returned no macro points for {start}..{end}")
        return tuple(points)

    def _replay_version(self, dataset_id: str, end: date) -> str:
        base = end.isoformat()
        existing = sum(
            1
            for v in self.pipeline.catalog.versions(dataset_id)
            if v.version == base or v.version.startswith(f"{base}#r")
        )
        return base if existing == 0 else f"{base}#r{existing}"

    def _run(
        self,
        dataset_id: str,
        version: str,
        frame: pl.DataFrame,
        schema: DatasetSchema,
        as_of: datetime | None,
    ) -> DatasetVersion:
        return self.pipeline.run_pipeline(
            dataset_id=dataset_id,
            version=version,
            source=self.source,
            frame=frame,
            schema=schema,
            as_of=as_of,
        )
