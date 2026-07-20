"""VCI (Vietcap) price adapter — fixtures (no network in CI).

Recorded, VCI-shaped OHLC payloads drive the adapter through a fake POST
transport: index and stock parsing, symbol selection from a multi-record
list, window filtering, per-ticker tolerance, pipeline storage, and the
registry membership. A live smoke test is opt-in, skipped otherwise.
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
from providers.connectors.vci_provider import VciProvider, create_vci_price_provider
from providers.registry_config import VCI, build_registry
from providers.sdk.registry import Capability

# 2026-01-05 and 2026-01-06 as unix seconds (UTC midnight).
_T5 = 1767571200
_T6 = 1767657600


def _record(symbol: str, closes: list[str], volumes: list[str]) -> dict[str, object]:
    return {
        "symbol": symbol,
        "t": [_T5, _T6],
        "o": closes,
        "h": closes,
        "l": closes,
        "c": closes,
        "v": volumes,
    }


FPT = _record("FPT", ["138.4", "140.6"], ["4900000", "5300000"])
VNINDEX = _record("VNINDEX", ["1284.56", "1293.11"], ["0", "0"])


class FakePostTransport:
    """Scripted VCI responses keyed by the first requested symbol."""

    def __init__(
        self, by_symbol: dict[str, dict[str, object]], *, fail: set[str] | None = None
    ) -> None:
        self.by_symbol = by_symbol
        self.fail = fail or set()
        self.calls: list[Mapping[str, object]] = []

    def post_json(self, url: str, body: Mapping[str, object], timeout: float) -> object:
        self.calls.append(body)
        symbols = body.get("symbols")
        symbol = symbols[0] if isinstance(symbols, list) and symbols else ""
        if symbol in self.fail:
            raise RuntimeError("simulated VCI 5xx")
        record = self.by_symbol.get(str(symbol))
        return [record] if record is not None else []


def _provider(**kw: object) -> VciProvider:
    transport = FakePostTransport({"FPT": FPT, "VNINDEX": VNINDEX}, **kw)  # type: ignore[arg-type]
    return VciProvider(transport=transport, max_attempts=2)


class TestParsing:
    def test_stock_bars(self) -> None:
        bars = _provider().daily_bars("FPT", date(2026, 1, 1), date(2026, 1, 31))
        assert [b.day.isoformat() for b in bars] == ["2026-01-05", "2026-01-06"]
        assert bars[-1].close == Decimal("140.6")
        assert bars[0].volume == Decimal("4900000")
        assert bars[0].ticker == "FPT"

    def test_index_symbol_and_daily_timeframe(self) -> None:
        provider = _provider()
        bars = provider.daily_bars("VNINDEX", date(2026, 1, 1), date(2026, 1, 31))
        assert bars[-1].close == Decimal("1293.11")
        call = provider.transport.calls[-1]  # type: ignore[attr-defined]
        assert call["symbols"] == ["VNINDEX"] and call["timeFrame"] == "ONE_DAY"

    def test_window_filter(self) -> None:
        bars = _provider().daily_bars("FPT", date(2026, 1, 6), date(2026, 1, 6))
        assert [b.day.isoformat() for b in bars] == ["2026-01-06"]

    def test_unknown_symbol_empty(self) -> None:
        assert _provider().daily_bars("ZZZ", date(2026, 1, 1), date(2026, 1, 31)) == ()

    def test_picks_matching_record_from_list(self) -> None:
        # A list carrying several records must select the requested symbol's.
        class MultiTransport:
            def post_json(self, url: str, body: Mapping[str, object], timeout: float) -> object:
                return [VNINDEX, FPT]  # two records; provider must pick FPT

        provider = VciProvider(transport=MultiTransport(), max_attempts=1)
        bars = provider.daily_bars("FPT", date(2026, 1, 1), date(2026, 1, 31))
        assert bars and bars[0].ticker == "FPT" and bars[-1].close == Decimal("140.6")


class TestTolerance:
    def test_failed_symbol_returns_empty_not_raise(self) -> None:
        provider = VciProvider(
            transport=FakePostTransport({"FPT": FPT}, fail={"FPT"}), max_attempts=2
        )
        assert provider.daily_bars("FPT", date(2026, 1, 1), date(2026, 1, 31)) == ()


class TestRegistry:
    def test_vci_is_registered_price_source(self) -> None:
        registry = build_registry()
        assert VCI in registry.names(Capability.PRICE)
        resolved = registry.resolve(Capability.PRICE, {Capability.PRICE.value: VCI})
        assert isinstance(resolved, VciProvider)


class TestPipelineStorage:
    def test_full_sync_publishes_indices_and_stocks(self) -> None:
        pipeline = DataPipelineUseCases(catalog=MemoryCatalog(), snapshots=MemorySnapshots())
        sync = ProviderSyncService(pipeline=pipeline, source="provider:vci")
        provider = create_vci_price_provider(
            transport=FakePostTransport({"FPT": FPT, "VNINDEX": VNINDEX})
        )
        version = sync.full_sync_prices(
            provider, ["VNINDEX", "FPT"], date(2026, 1, 1), date(2026, 1, 31)
        )
        assert version.status is DatasetStatus.PUBLISHED
        frame = pipeline.read_published(PRICES_DATASET)
        assert {"VNINDEX", "FPT"} <= set(frame["ticker"].to_list())


@pytest.mark.skipif(
    os.environ.get("VCI_LIVE") != "1",
    reason="live VCI call — set VCI_LIVE=1 on open internet",
)
def test_live_vnindex() -> None:
    provider = create_vci_price_provider()
    bars = provider.daily_bars("VNINDEX", date(2026, 1, 2), date(2026, 1, 15))
    assert bars, "expected live VNINDEX bars from VCI"
