"""PublishedMarketPriceReader.ohlc_for — OHLC extraction for candlesticks."""

from __future__ import annotations

from datetime import datetime, timezone

import polars as pl

from infrastructure.market_read import PublishedMarketPriceReader
from shared_kernel.exceptions import NotFoundError


class _Pipeline:
    def __init__(self, frame: pl.DataFrame | None) -> None:
        self._frame = frame

    def read_published(self, _dataset: str) -> pl.DataFrame:
        if self._frame is None:
            raise NotFoundError("no prices")
        return self._frame


def _day(d: int) -> datetime:
    return datetime(2026, 7, d, tzinfo=timezone.utc)


def test_ohlc_for_returns_sorted_ohlc_for_ticker() -> None:
    frame = pl.DataFrame(
        {
            "ticker": ["FPT", "FPT", "VCB"],
            "day": [_day(2), _day(1), _day(1)],
            "open": ["100", "98", "50"],
            "high": ["110", "101", "52"],
            "low": ["97", "96", "49"],
            "close": ["105", "99", "51"],
            "volume": ["1000", "900", "800"],
        }
    )
    bars = PublishedMarketPriceReader(_Pipeline(frame)).ohlc_for("fpt")
    assert [b["day"] for b in bars] == ["2026-07-01", "2026-07-02"]  # sorted, FPT only
    assert bars[0] == {
        "day": "2026-07-01",
        "open": 98.0,
        "high": 101.0,
        "low": 96.0,
        "close": 99.0,
        "volume": 900.0,
    }


def test_ohlc_for_tolerates_missing_ohl_columns() -> None:
    frame = pl.DataFrame({"ticker": ["FPT"], "day": [_day(1)], "close": ["105"]})
    bars = PublishedMarketPriceReader(_Pipeline(frame)).ohlc_for("FPT")
    assert bars == [
        {
            "day": "2026-07-01",
            "open": None,
            "high": None,
            "low": None,
            "close": 105.0,
            "volume": None,
        }
    ]


def test_ohlc_for_empty_when_nothing_published() -> None:
    assert PublishedMarketPriceReader(_Pipeline(None)).ohlc_for("FPT") == []
