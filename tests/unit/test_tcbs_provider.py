"""TCBS public-API price adapter — fixtures (no network in CI).

Recorded, TCBS-shaped bars drive the adapter through a fake transport: index
and stock parsing, window filtering, per-ticker tolerance, pipeline storage,
and the registry default. A live smoke test is opt-in (VN data host + open
internet), skipped otherwise.
"""

from __future__ import annotations

import os
from datetime import date
from decimal import Decimal
from typing import Mapping

import pytest
from tests.unit.test_production_sync import MemoryCatalog, MemorySnapshots

from data_pipeline.application.sync import PRICES_DATASET, ProviderSyncService
from data_pipeline.application.use_cases import DataPipelineUseCases
from data_pipeline.domain.dataset import DatasetStatus
from providers.connectors.chained_price import ChainedPriceProvider
from providers.connectors.tcbs_provider import TcbsProvider, create_tcbs_price_provider
from providers.registry_config import DEFAULT_SELECTION, TCBS, build_registry
from providers.sdk.registry import Capability

Record = dict[str, object]


def _bars(rows: list[tuple[str, str, str]]) -> list[Record]:
    # (tradingDate, close, volume)
    return [
        {
            "tradingDate": d,
            "open": c,
            "high": c,
            "low": c,
            "close": c,
            "volume": v,
        }
        for d, c, v in rows
    ]


FPT = _bars(
    [
        ("2026-01-05T00:00:00.000Z", "138.4", "4900000"),
        ("2026-01-06T00:00:00.000Z", "140.6", "5300000"),
    ]
)
VNINDEX = _bars(
    [("2026-01-05T00:00:00.000Z", "1284.56", "0"), ("2026-01-06T00:00:00.000Z", "1293.11", "0")]
)


class FakeTransport:
    """Scripted TCBS responses keyed by ticker; can also fail on demand."""

    def __init__(self, by_ticker: dict[str, list[Record]], *, fail: set[str] | None = None) -> None:
        self.by_ticker = by_ticker
        self.fail = fail or set()
        self.calls: list[Mapping[str, str]] = []

    def get_json(self, url: str, params: Mapping[str, str], timeout: float) -> Mapping[str, object]:
        self.calls.append(params)
        ticker = params["ticker"]
        if ticker in self.fail:
            raise RuntimeError("simulated TCBS 5xx")
        return {"data": self.by_ticker.get(ticker, []), "ticker": ticker}


def _provider(**kw: object) -> TcbsProvider:
    transport = FakeTransport({"FPT": FPT, "VNINDEX": VNINDEX}, **kw)  # type: ignore[arg-type]
    return TcbsProvider(transport=transport, max_attempts=2)


class TestParsing:
    def test_stock_bars(self) -> None:
        bars = _provider().daily_bars("FPT", date(2026, 1, 1), date(2026, 1, 31))
        assert [b.day.isoformat() for b in bars] == ["2026-01-05", "2026-01-06"]
        assert bars[-1].close == Decimal("140.6")
        assert bars[0].volume == Decimal("4900000")
        assert bars[0].ticker == "FPT"

    def test_index_uses_type_index(self) -> None:
        provider = _provider()
        bars = provider.daily_bars("VNINDEX", date(2026, 1, 1), date(2026, 1, 31))
        assert bars[-1].close == Decimal("1293.11")
        # the request asked TCBS for an index, not a stock
        call = provider.transport.calls[-1]  # type: ignore[attr-defined]
        assert call["type"] == "index" and call["ticker"] == "VNINDEX"

    def test_window_filter(self) -> None:
        bars = _provider().daily_bars("FPT", date(2026, 1, 6), date(2026, 1, 6))
        assert [b.day.isoformat() for b in bars] == ["2026-01-06"]

    def test_unknown_ticker_empty(self) -> None:
        assert _provider().daily_bars("ZZZ", date(2026, 1, 1), date(2026, 1, 31)) == ()


class TestTolerance:
    def test_failed_ticker_returns_empty_not_raise(self) -> None:
        provider = TcbsProvider(transport=FakeTransport({"FPT": FPT}, fail={"FPT"}), max_attempts=2)
        # Two attempts both raise inside the transport → tolerated → empty tuple.
        assert provider.daily_bars("FPT", date(2026, 1, 1), date(2026, 1, 31)) == ()


class TestRegistry:
    def test_tcbs_is_registered_as_a_price_source(self) -> None:
        registry = build_registry()
        assert TCBS in registry.names(Capability.PRICE)
        resolved = registry.resolve(Capability.PRICE, {Capability.PRICE.value: TCBS})
        assert isinstance(resolved, TcbsProvider)

    def test_default_price_provider_is_not_the_chain(self) -> None:
        # Automatic failover is off by default: the default price provider is
        # single-source vnstock, not the ChainedPriceProvider.
        assert DEFAULT_SELECTION[Capability.PRICE.value] != TCBS
        registry = build_registry()
        resolved = registry.resolve(Capability.PRICE, DEFAULT_SELECTION)
        assert not isinstance(resolved, ChainedPriceProvider)


class TestPipelineStorage:
    def test_full_sync_publishes_indices_and_stocks(self) -> None:
        pipeline = DataPipelineUseCases(catalog=MemoryCatalog(), snapshots=MemorySnapshots())
        sync = ProviderSyncService(pipeline=pipeline, source="provider:tcbs")
        provider = create_tcbs_price_provider(
            transport=FakeTransport({"FPT": FPT, "VNINDEX": VNINDEX})
        )
        version = sync.full_sync_prices(
            provider, ["VNINDEX", "FPT"], date(2026, 1, 1), date(2026, 1, 31)
        )
        assert version.status is DatasetStatus.PUBLISHED
        frame = pipeline.read_published(PRICES_DATASET)
        assert {"VNINDEX", "FPT"} <= set(frame["ticker"].to_list())

    def test_sync_survives_a_bad_ticker(self) -> None:
        pipeline = DataPipelineUseCases(catalog=MemoryCatalog(), snapshots=MemorySnapshots())
        sync = ProviderSyncService(pipeline=pipeline, source="provider:tcbs")
        provider = create_tcbs_price_provider(
            transport=FakeTransport({"FPT": FPT, "VNINDEX": VNINDEX}, fail={"FPT"})
        )
        # FPT fails, VNINDEX succeeds → sync still publishes.
        version = sync.full_sync_prices(
            provider, ["VNINDEX", "FPT"], date(2026, 1, 1), date(2026, 1, 31)
        )
        assert version.status is DatasetStatus.PUBLISHED
        assert set(pipeline.read_published(PRICES_DATASET)["ticker"].to_list()) == {"VNINDEX"}


@pytest.mark.skipif(
    os.environ.get("TCBS_LIVE") != "1",
    reason="live TCBS call — set TCBS_LIVE=1 on open internet",
)
def test_live_vnindex() -> None:
    provider = create_tcbs_price_provider()
    bars = provider.daily_bars("VNINDEX", date(2026, 1, 2), date(2026, 1, 15))
    assert bars, "expected live VNINDEX bars from TCBS"
