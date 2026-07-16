"""Local-file provider (Phase 2, Module 2) — CSV-backed adapter.

Reads vendor data dumps from a directory (prices.csv, macro.csv,
fx.csv, sectors.csv, calendar.csv) via Polars. Deterministic, offline,
and the reference connector for on-premise data drops. Adapters only:
no business logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path

import polars as pl

from providers.sdk.models import FxRate, MacroPoint, PriceBar, SectorMapping
from shared_kernel.exceptions import DomainError


class LocalDataError(DomainError):
    """Missing or malformed local data files."""


@dataclass(frozen=True, slots=True)
class LocalFileProvider:
    """Price/Macro/FX/Sector/Calendar capabilities from CSV files."""

    directory: Path

    def _frame(self, filename: str) -> pl.DataFrame:
        path = self.directory / filename
        if not path.exists():
            raise LocalDataError(f"data file not found: {path}")
        return pl.read_csv(path)

    def daily_bars(self, ticker: str, start: date, end: date) -> tuple[PriceBar, ...]:
        frame = self._frame("prices.csv").filter(pl.col("ticker") == ticker)
        bars = []
        for row in frame.iter_rows(named=True):
            day = date.fromisoformat(str(row["day"]))
            if start <= day <= end:
                bars.append(
                    PriceBar(
                        ticker=ticker,
                        day=day,
                        close=Decimal(str(row["close"])),
                        volume=(
                            Decimal(str(row["volume"])) if row.get("volume") is not None else None
                        ),
                    )
                )
        return tuple(sorted(bars, key=lambda b: b.day))

    def series(self, indicator: str, start: date, end: date) -> tuple[MacroPoint, ...]:
        frame = self._frame("macro.csv").filter(pl.col("indicator") == indicator)
        points = []
        for row in frame.iter_rows(named=True):
            day = date.fromisoformat(str(row["day"]))
            if start <= day <= end:
                points.append(
                    MacroPoint(indicator=indicator, day=day, value=Decimal(str(row["value"])))
                )
        return tuple(sorted(points, key=lambda p: p.day))

    def rate(self, pair: str, day: date) -> FxRate | None:
        frame = self._frame("fx.csv").filter(pl.col("pair") == pair)
        best: FxRate | None = None
        for row in frame.iter_rows(named=True):
            row_day = date.fromisoformat(str(row["day"]))
            if row_day <= day and (best is None or row_day > best.day):
                best = FxRate(pair=pair, day=row_day, rate=Decimal(str(row["rate"])))
        return best

    def classification(self, ticker: str) -> SectorMapping | None:
        frame = self._frame("sectors.csv").filter(pl.col("ticker") == ticker)
        for row in frame.iter_rows(named=True):
            return SectorMapping(
                ticker=ticker,
                sector=str(row["sector"]),
                industry=str(row["industry"]),
                exchange=str(row.get("exchange", "")),
            )
        return None

    def trading_days(self, start: date, end: date) -> tuple[date, ...]:
        frame = self._frame("calendar.csv")
        days = [date.fromisoformat(str(row["day"])) for row in frame.iter_rows(named=True)]
        return tuple(sorted(d for d in days if start <= d <= end))
