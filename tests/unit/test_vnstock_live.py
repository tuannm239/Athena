"""Opt-in live vnstock integration test (VNSTOCK_LIVE=1).

Verifies the real end-to-end path with no mocks: the production vnstock price
provider fetches VN market data and the *existing* ProviderSyncService persists
it through the Data Pipeline (in-memory catalog/snapshot store — no DB needed).

Skipped automatically unless VNSTOCK_LIVE=1 and the environment can reach the
VCI data host. It is never run in normal CI.
"""

from __future__ import annotations

import os
from datetime import date, timedelta

import pytest
from tests.unit.test_production_sync import MemoryCatalog, MemorySnapshots

from data_pipeline.application.sync import PRICES_DATASET, ProviderSyncService
from data_pipeline.application.use_cases import DataPipelineUseCases
from data_pipeline.domain.dataset import DatasetStatus
from providers.registry_config import DEFAULT_SELECTION, build_registry
from providers.sdk.registry import Capability

pytestmark = pytest.mark.skipif(
    os.environ.get("VNSTOCK_LIVE") != "1",
    reason="live vnstock integration — set VNSTOCK_LIVE=1 on a VN-reachable network",
)


def _price_provider():  # type: ignore[no-untyped-def]
    # The configured production provider (vnstock, routed by VNSTOCK_SOURCE).
    return build_registry().resolve(Capability.PRICE, DEFAULT_SELECTION)


def test_provider_connectivity_returns_real_bars() -> None:
    provider = _price_provider()
    end = date.today()
    bars = provider.daily_bars("VNINDEX", end - timedelta(days=15), end)
    assert bars, "expected live VNINDEX bars from vnstock/VCI"
    assert bars[-1].close > 0


def test_sync_persists_through_existing_pipeline() -> None:
    pipeline = DataPipelineUseCases(catalog=MemoryCatalog(), snapshots=MemorySnapshots())
    sync = ProviderSyncService(pipeline=pipeline, source="provider:vnstock")
    provider = _price_provider()
    end = date.today()
    version = sync.full_sync_prices(provider, ["VNINDEX", "FPT"], end - timedelta(days=15), end)
    assert version.status is DatasetStatus.PUBLISHED
    frame = pipeline.read_published(PRICES_DATASET)
    assert "VNINDEX" in set(frame["ticker"].to_list())
