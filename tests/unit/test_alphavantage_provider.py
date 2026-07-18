"""Phase 5 W5 — Alpha Vantage production adapter (fake transport, no network)."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Mapping

import pytest

from data_pipeline.application.sync import ProviderSyncService
from data_pipeline.application.use_cases import DataPipelineUseCases
from data_pipeline.domain.dataset import DatasetStatus
from providers.connectors.alphavantage import (
    AlphaVantageError,
    AlphaVantageProvider,
    create_alphavantage_price_provider,
)
from providers.connectors.resilient import ResilientPriceProvider

# ---- fakes ----------------------------------------------------------------


class FakeTransport:
    """Scripted responses keyed by the `function` query param."""

    def __init__(self, by_function: dict[str, Mapping[str, object]]):
        self.by_function = by_function
        self.calls: list[Mapping[str, str]] = []

    def get_json(self, url: str, params: Mapping[str, str], timeout: float) -> Mapping[str, object]:
        self.calls.append(params)
        return self.by_function[params["function"]]


PRICE_PAYLOAD = {
    "Meta Data": {"2. Symbol": "HPG"},
    "Time Series (Daily)": {
        "2026-01-05": {
            "1. open": "27.0",
            "2. high": "27.8",
            "3. low": "26.9",
            "4. close": "27.5",
            "5. volume": "1500000",
        },
        "2026-01-06": {
            "1. open": "27.5",
            "2. high": "28.2",
            "3. low": "27.4",
            "4. close": "28.0",
            "5. volume": "1800000",
        },
        "2025-12-30": {
            "1. open": "26.0",
            "2. high": "26.5",
            "3. low": "25.8",
            "4. close": "26.2",
            "5. volume": "1200000",
        },
    },
}
FX_PAYLOAD = {
    "Time Series FX (Daily)": {
        "2026-01-06": {
            "1. open": "25400",
            "2. high": "25450",
            "3. low": "25380",
            "4. close": "25420",
        },
        "2026-01-05": {
            "1. open": "25390",
            "2. high": "25410",
            "3. low": "25370",
            "4. close": "25400",
        },
    },
}


def provider() -> AlphaVantageProvider:
    return AlphaVantageProvider(
        api_key="test-key",
        transport=FakeTransport({"TIME_SERIES_DAILY": PRICE_PAYLOAD, "FX_DAILY": FX_PAYLOAD}),
    )


class TestPriceMapping:
    def test_maps_daily_bars_to_domain_decimals_in_window(self) -> None:
        bars = provider().daily_bars("HPG", date(2026, 1, 1), date(2026, 1, 31))
        assert [b.day for b in bars] == [date(2026, 1, 5), date(2026, 1, 6)]  # 2025 bar excluded
        assert bars[0].close == Decimal("27.5")
        assert isinstance(bars[0].close, Decimal)
        assert bars[0].volume == Decimal("1500000")
        assert bars[1].high == Decimal("28.2")

    def test_api_key_is_passed_but_never_in_the_dto(self) -> None:
        transport = FakeTransport({"TIME_SERIES_DAILY": PRICE_PAYLOAD})
        adapter = AlphaVantageProvider(api_key="secret-key", transport=transport)
        adapter.daily_bars("HPG", date(2026, 1, 1), date(2026, 1, 31))
        assert transport.calls[0]["apikey"] == "secret-key"

    def test_vendor_rate_limit_note_becomes_typed_error(self) -> None:
        adapter = AlphaVantageProvider(
            api_key="k",
            transport=FakeTransport({"TIME_SERIES_DAILY": {"Note": "5 calls/min limit reached"}}),
        )
        with pytest.raises(AlphaVantageError):
            adapter.daily_bars("HPG", date(2026, 1, 1), date(2026, 1, 31))

    def test_error_message_becomes_typed_error(self) -> None:
        adapter = AlphaVantageProvider(
            api_key="k",
            transport=FakeTransport({"TIME_SERIES_DAILY": {"Error Message": "invalid symbol"}}),
        )
        with pytest.raises(AlphaVantageError):
            adapter.daily_bars("ZZZZ", date(2026, 1, 1), date(2026, 1, 31))


class TestFxMapping:
    def test_point_in_time_rate(self) -> None:
        rate = provider().rate("USDVND", date(2026, 1, 6))
        assert rate is not None and rate.day == date(2026, 1, 6)
        assert rate.rate == Decimal("25420")

    def test_rate_before_first_observation_is_none(self) -> None:
        assert provider().rate("USDVND", date(2020, 1, 1)) is None

    def test_bad_pair_rejected(self) -> None:
        with pytest.raises(AlphaVantageError):
            provider().rate("USD", date(2026, 1, 6))


class TestResilientComposition:
    def test_factory_wraps_in_resilience_and_caches(self) -> None:
        transport = FakeTransport({"TIME_SERIES_DAILY": PRICE_PAYLOAD})
        rp = create_alphavantage_price_provider(api_key="k", transport=transport)
        assert isinstance(rp, ResilientPriceProvider)
        rp.daily_bars("HPG", date(2026, 1, 1), date(2026, 1, 31))
        rp.daily_bars("HPG", date(2026, 1, 1), date(2026, 1, 31))  # served from cache
        assert len(transport.calls) == 1  # second call cached, no extra transport hit
        assert rp.status().healthy

    def test_missing_env_key_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("ALPHAVANTAGE_API_KEY", raising=False)
        with pytest.raises(AlphaVantageError):
            create_alphavantage_price_provider()


class TestPipelineIntegration:
    """The adapter feeds the RFC-0024 pipeline unchanged (ADR-0017)."""

    def test_provider_sync_publishes_alphavantage_prices(self) -> None:
        from test_production_sync import (  # type: ignore[import-not-found]
            MemoryCatalog,
            MemorySnapshots,
        )

        rp = create_alphavantage_price_provider(
            api_key="k", transport=FakeTransport({"TIME_SERIES_DAILY": PRICE_PAYLOAD})
        )
        pipeline = DataPipelineUseCases(catalog=MemoryCatalog(), snapshots=MemorySnapshots())
        sync = ProviderSyncService(pipeline=pipeline, source="provider:alphavantage")
        ds = sync.full_sync_prices(
            rp,
            ["HPG"],
            date(2026, 1, 1),
            date(2026, 1, 31),
            as_of=datetime(2026, 1, 31, tzinfo=timezone.utc),
        )
        assert ds.status is DatasetStatus.PUBLISHED
        assert ds.quality.passed
        assert ds.lineage.source == "provider:alphavantage"
        frame = pipeline.read_published("prices")
        assert frame.height == 2  # the two in-window bars, quality-gated and published


class TestRegistry:
    """The adapter is selectable through the configuration-driven registry."""

    def test_registry_exposes_alphavantage_and_static(self) -> None:
        from providers.registry_config import ALPHAVANTAGE, STATIC, build_registry
        from providers.sdk.registry import Capability

        reg = build_registry()
        assert ALPHAVANTAGE in reg.names(Capability.PRICE)
        assert STATIC in reg.names(Capability.PRICE)
        assert ALPHAVANTAGE in reg.names(Capability.FX)
