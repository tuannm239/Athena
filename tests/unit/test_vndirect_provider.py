"""VNDirect dchart price adapter + VN price chain — fixtures (no network in CI).

Recorded, VNDirect-UDF-shaped payloads drive the adapter through a fake
transport: index and stock parsing, window filtering, per-ticker tolerance,
the `s != "ok"` guard, and the VNDirect→TCBS fallback chain. A live smoke test
is opt-in (VN data host + open internet), skipped otherwise.
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
from providers.connectors.chained_price import (
    ChainedPriceProvider,
    create_chained_price_provider,
)
from providers.connectors.vndirect_provider import (
    VndirectProvider,
    create_vndirect_price_provider,
)
from providers.registry_config import DEFAULT_SELECTION, VNDIRECT, build_registry
from providers.sdk.models import PriceBar
from providers.sdk.registry import Capability

# 2026-01-05 and 2026-01-06 as unix seconds (UTC midnight).
_T5 = 1767571200
_T6 = 1767657600


def _udf(times: list[int], closes: list[str], volumes: list[str]) -> dict[str, object]:
    return {
        "s": "ok",
        "t": times,
        "o": closes,
        "h": closes,
        "l": closes,
        "c": closes,
        "v": volumes,
    }


FPT = _udf([_T5, _T6], ["138.4", "140.6"], ["4900000", "5300000"])
VNINDEX = _udf([_T5, _T6], ["1284.56", "1293.11"], ["0", "0"])


class FakeTransport:
    """Scripted VNDirect responses keyed by symbol; can also fail on demand."""

    def __init__(
        self, by_symbol: dict[str, dict[str, object]], *, fail: set[str] | None = None
    ) -> None:
        self.by_symbol = by_symbol
        self.fail = fail or set()
        self.calls: list[Mapping[str, str]] = []

    def get_json(self, url: str, params: Mapping[str, str], timeout: float) -> Mapping[str, object]:
        self.calls.append(params)
        symbol = params["symbol"]
        if symbol in self.fail:
            raise RuntimeError("simulated VNDirect 5xx")
        return self.by_symbol.get(symbol, {"s": "no_data"})


def _provider(**kw: object) -> VndirectProvider:
    transport = FakeTransport({"FPT": FPT, "VNINDEX": VNINDEX}, **kw)  # type: ignore[arg-type]
    return VndirectProvider(transport=transport, max_attempts=2)


class TestParsing:
    def test_stock_bars(self) -> None:
        bars = _provider().daily_bars("FPT", date(2026, 1, 1), date(2026, 1, 31))
        assert [b.day.isoformat() for b in bars] == ["2026-01-05", "2026-01-06"]
        assert bars[-1].close == Decimal("140.6")
        assert bars[0].volume == Decimal("4900000")
        assert bars[0].ticker == "FPT"

    def test_index_symbol_passed_through(self) -> None:
        provider = _provider()
        bars = provider.daily_bars("VNINDEX", date(2026, 1, 1), date(2026, 1, 31))
        assert bars[-1].close == Decimal("1293.11")
        call = provider.transport.calls[-1]  # type: ignore[attr-defined]
        assert call["symbol"] == "VNINDEX" and call["resolution"] == "D"

    def test_window_filter(self) -> None:
        bars = _provider().daily_bars("FPT", date(2026, 1, 6), date(2026, 1, 6))
        assert [b.day.isoformat() for b in bars] == ["2026-01-06"]

    def test_no_data_status_is_empty(self) -> None:
        assert _provider().daily_bars("ZZZ", date(2026, 1, 1), date(2026, 1, 31)) == ()


class TestTolerance:
    def test_failed_symbol_returns_empty_not_raise(self) -> None:
        provider = VndirectProvider(
            transport=FakeTransport({"FPT": FPT}, fail={"FPT"}), max_attempts=2
        )
        assert provider.daily_bars("FPT", date(2026, 1, 1), date(2026, 1, 31)) == ()


class TestRegistry:
    def test_vndirect_registered_and_default_is_chain(self) -> None:
        registry = build_registry()
        assert VNDIRECT in registry.names(Capability.PRICE)
        resolved = registry.resolve(Capability.PRICE, DEFAULT_SELECTION)
        assert isinstance(resolved, ChainedPriceProvider)


class _StubSource:
    """A minimal PriceProvider returning a fixed result, recording calls."""

    def __init__(self, result: tuple[PriceBar, ...], *, boom: bool = False) -> None:
        self.result = result
        self.boom = boom
        self.called = False

    def daily_bars(self, ticker: str, start: date, end: date) -> tuple[PriceBar, ...]:
        self.called = True
        if self.boom:
            raise RuntimeError("stub source failure")
        return self.result


def _bar() -> PriceBar:
    return PriceBar(ticker="X", day=date(2026, 1, 6), close=Decimal("10"))


class TestChain:
    def test_first_non_empty_wins_and_short_circuits(self) -> None:
        primary = _StubSource((_bar(),))
        secondary = _StubSource((_bar(),))
        chain = create_chained_price_provider(primary, secondary)
        bars = chain.daily_bars("X", date(2026, 1, 1), date(2026, 1, 31))
        assert bars and primary.called and not secondary.called

    def test_falls_through_empty_source(self) -> None:
        primary = _StubSource(())
        secondary = _StubSource((_bar(),))
        chain = create_chained_price_provider(primary, secondary)
        bars = chain.daily_bars("X", date(2026, 1, 1), date(2026, 1, 31))
        assert bars and primary.called and secondary.called

    def test_falls_through_raising_source(self) -> None:
        primary = _StubSource((), boom=True)
        secondary = _StubSource((_bar(),))
        chain = create_chained_price_provider(primary, secondary)
        bars = chain.daily_bars("X", date(2026, 1, 1), date(2026, 1, 31))
        assert bars and secondary.called

    def test_all_empty_returns_empty(self) -> None:
        chain = create_chained_price_provider(_StubSource(()), _StubSource(()))
        assert chain.daily_bars("X", date(2026, 1, 1), date(2026, 1, 31)) == ()

    def test_requires_at_least_one_source(self) -> None:
        with pytest.raises(ValueError):
            create_chained_price_provider()


class TestPipelineStorage:
    def test_full_sync_publishes_indices_and_stocks(self) -> None:
        pipeline = DataPipelineUseCases(catalog=MemoryCatalog(), snapshots=MemorySnapshots())
        sync = ProviderSyncService(pipeline=pipeline, source="provider:vndirect")
        provider = create_vndirect_price_provider(
            transport=FakeTransport({"FPT": FPT, "VNINDEX": VNINDEX})
        )
        version = sync.full_sync_prices(
            provider, ["VNINDEX", "FPT"], date(2026, 1, 1), date(2026, 1, 31)
        )
        assert version.status is DatasetStatus.PUBLISHED
        frame = pipeline.read_published(PRICES_DATASET)
        assert {"VNINDEX", "FPT"} <= set(frame["ticker"].to_list())


@pytest.mark.skipif(
    os.environ.get("VNDIRECT_LIVE") != "1",
    reason="live VNDirect call — set VNDIRECT_LIVE=1 on open internet",
)
def test_live_vnindex() -> None:
    provider = create_vndirect_price_provider()
    bars = provider.daily_bars("VNINDEX", date(2026, 1, 2), date(2026, 1, 15))
    assert bars, "expected live VNINDEX bars from VNDirect"
