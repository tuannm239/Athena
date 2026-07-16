"""Phase 2 Module 3 — provider → pipeline / KG / decision-pipeline sync."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

import polars as pl
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from data_pipeline.application.facts import PublishedPriceFacts
from data_pipeline.application.sync import (
    FUNDAMENTALS_DATASET,
    FX_DATASET,
    MACRO_DATASET,
    PRICES_DATASET,
    ProviderSyncService,
    SyncError,
)
from data_pipeline.application.use_cases import DataPipelineUseCases
from data_pipeline.domain.dataset import DatasetStatus, DatasetVersion
from data_pipeline.domain.repository import DatasetCatalog
from infrastructure.db.base import Base
from infrastructure.db.repositories.graph_store import SqlGraphStore
from knowledge.application.sync import KnowledgeSyncService
from knowledge.application.use_cases import KnowledgeGraphUseCases
from providers.connectors.static import StaticProvider
from providers.sdk.models import (
    FundamentalRecord,
    FxRate,
    MacroPoint,
    PriceBar,
    SectorMapping,
)

AS_OF = datetime(2026, 7, 10, 18, 0, tzinfo=timezone.utc)


class MemoryCatalog(DatasetCatalog):
    def __init__(self) -> None:
        self._rows: dict[tuple[str, str], DatasetVersion] = {}
        self._order: list[tuple[str, str]] = []

    def save(self, dataset: DatasetVersion) -> None:
        key = (dataset.dataset_id, dataset.version)
        self._rows[key] = dataset
        self._order.append(key)

    def get(self, dataset_id: str, version: str) -> DatasetVersion | None:
        return self._rows.get((dataset_id, version))

    def latest(
        self, dataset_id: str, *, status: DatasetStatus | None = None
    ) -> DatasetVersion | None:
        for key in reversed(self._order):
            row = self._rows[key]
            if row.dataset_id == dataset_id and (status is None or row.status is status):
                return row
        return None

    def versions(self, dataset_id: str) -> tuple[DatasetVersion, ...]:
        return tuple(self._rows[k] for k in self._order if k[0] == dataset_id)

    def set_status(self, dataset_id: str, version: str, status: DatasetStatus) -> None:
        row = self._rows[(dataset_id, version)]
        self._rows[(dataset_id, version)] = DatasetVersion(
            dataset_id=row.dataset_id,
            version=row.version,
            snapshot_id=row.snapshot_id,
            status=status,
            lineage=row.lineage,
            quality=row.quality,
            created_at=row.created_at,
        )


class MemorySnapshots:
    def __init__(self) -> None:
        self.tables: dict[tuple[str, str], pl.DataFrame] = {}

    def write(self, snapshot_id: str, table: str, frame: pl.DataFrame) -> None:
        self.tables[(snapshot_id, table)] = frame

    def read(self, snapshot_id: str, table: str) -> pl.DataFrame:
        return self.tables[(snapshot_id, table)]


def bar(ticker: str, day: date, close: str, volume: str | None = "1000") -> PriceBar:
    return PriceBar(
        ticker=ticker,
        day=day,
        close=Decimal(close),
        volume=Decimal(volume) if volume is not None else None,
    )


def provider() -> StaticProvider:
    return StaticProvider(
        bars=(
            bar("AAA", date(2026, 7, 8), "10.5"),
            bar("AAA", date(2026, 7, 9), "10.75"),
            bar("AAA", date(2026, 7, 10), "11"),
            bar("BBB", date(2026, 7, 9), "20", volume=None),
            bar("BBB", date(2026, 7, 10), "21"),
        ),
        macro_points=(
            MacroPoint("interest_rate", date(2026, 7, 9), Decimal("4.5")),
            MacroPoint("interest_rate", date(2026, 7, 10), Decimal("4.25")),
        ),
        fundamental_records=(
            FundamentalRecord("AAA", "2026Q2", "roe", Decimal("0.18")),
            FundamentalRecord("BBB", "2026Q2", "roe", Decimal("0.09")),
        ),
        fx_rates=(FxRate("USDVND", date(2026, 7, 10), Decimal("25400")),),
        sectors=(
            SectorMapping("AAA", "Materials", "Steel", exchange="HOSE"),
            SectorMapping("BBB", "Financials", "Banks"),
        ),
    )


@pytest.fixture()
def pipeline() -> DataPipelineUseCases:
    return DataPipelineUseCases(catalog=MemoryCatalog(), snapshots=MemorySnapshots())


@pytest.fixture()
def sync(pipeline: DataPipelineUseCases) -> ProviderSyncService:
    return ProviderSyncService(pipeline=pipeline, source="provider:static")


class TestFullSync:
    def test_full_sync_publishes_with_lineage(
        self, sync: ProviderSyncService, pipeline: DataPipelineUseCases
    ) -> None:
        dataset = sync.full_sync_prices(
            provider(), ["BBB", "AAA"], date(2026, 7, 8), date(2026, 7, 10), as_of=AS_OF
        )
        assert dataset.status is DatasetStatus.PUBLISHED
        assert dataset.version == "2026-07-10"
        assert dataset.lineage.source == "provider:static"
        assert dataset.quality.passed
        frame = pipeline.read_published(PRICES_DATASET)
        assert frame.height == 5
        assert frame["close"].to_list()[0] == "10.5"  # Decimal fidelity via strings

    def test_empty_window_is_sync_error(self, sync: ProviderSyncService) -> None:
        with pytest.raises(SyncError):
            sync.full_sync_prices(
                provider(), ["AAA"], date(2020, 1, 1), date(2020, 1, 5), as_of=AS_OF
            )

    def test_future_bars_are_quarantined(self, sync: ProviderSyncService) -> None:
        early = datetime(2026, 7, 9, tzinfo=timezone.utc)
        dataset = sync.full_sync_prices(
            provider(), ["AAA"], date(2026, 7, 8), date(2026, 7, 10), as_of=early
        )
        assert dataset.status is DatasetStatus.QUARANTINED
        assert dataset.quality.quarantined_rows == 1  # the 2026-07-10 bar


class TestIncrementalSync:
    def test_requires_baseline_or_initial_start(self, sync: ProviderSyncService) -> None:
        with pytest.raises(SyncError):
            sync.incremental_sync_prices(provider(), ["AAA"], as_of=AS_OF)

    def test_initial_start_bootstraps(self, sync: ProviderSyncService) -> None:
        dataset = sync.incremental_sync_prices(
            provider(), ["AAA", "BBB"], as_of=AS_OF, initial_start=date(2026, 7, 8)
        )
        assert dataset is not None and dataset.version == "2026-07-10"
        assert sync.watermark(PRICES_DATASET) == date(2026, 7, 10)

    def test_syncs_only_after_watermark(
        self, sync: ProviderSyncService, pipeline: DataPipelineUseCases
    ) -> None:
        sync.full_sync_prices(
            provider(),
            ["AAA", "BBB"],
            date(2026, 7, 8),
            date(2026, 7, 9),
            as_of=datetime(2026, 7, 9, 18, 0, tzinfo=timezone.utc),
        )
        dataset = sync.incremental_sync_prices(provider(), ["AAA", "BBB"], as_of=AS_OF)
        assert dataset is not None and dataset.version == "2026-07-10"
        frame = pipeline.snapshots.read(dataset.snapshot_id, "data")
        assert frame.height == 2  # only the 2026-07-10 bars
        # up to date: second run is a no-op
        assert sync.incremental_sync_prices(provider(), ["AAA", "BBB"], as_of=AS_OF) is None

    def test_rollback_rewinds_watermark(self, sync: ProviderSyncService) -> None:
        sync.full_sync_prices(
            provider(),
            ["AAA"],
            date(2026, 7, 8),
            date(2026, 7, 9),
            as_of=datetime(2026, 7, 9, 18, 0, tzinfo=timezone.utc),
        )
        sync.incremental_sync_prices(provider(), ["AAA"], as_of=AS_OF)
        assert sync.watermark(PRICES_DATASET) == date(2026, 7, 10)
        sync.rollback(PRICES_DATASET, "2026-07-10")
        assert sync.watermark(PRICES_DATASET) == date(2026, 7, 9)


class TestReplay:
    def test_replay_lands_as_new_version(self, sync: ProviderSyncService) -> None:
        sync.full_sync_prices(provider(), ["AAA"], date(2026, 7, 8), date(2026, 7, 10), as_of=AS_OF)
        replay = sync.replay_prices(
            provider(), ["AAA"], date(2026, 7, 8), date(2026, 7, 10), as_of=AS_OF
        )
        assert replay.version == "2026-07-10#r1"
        second = sync.replay_prices(
            provider(), ["AAA"], date(2026, 7, 8), date(2026, 7, 10), as_of=AS_OF
        )
        assert second.version == "2026-07-10#r2"

    def test_replay_without_original_uses_base_version(self, sync: ProviderSyncService) -> None:
        replay = sync.replay_prices(
            provider(), ["AAA"], date(2026, 7, 8), date(2026, 7, 10), as_of=AS_OF
        )
        assert replay.version == "2026-07-10"


class TestOtherDatasets:
    def test_macro_full_and_incremental(self, sync: ProviderSyncService) -> None:
        dataset = sync.full_sync_macro(
            provider(),
            ["interest_rate"],
            date(2026, 7, 9),
            date(2026, 7, 9),
            as_of=datetime(2026, 7, 9, 18, 0, tzinfo=timezone.utc),
        )
        assert dataset.status is DatasetStatus.PUBLISHED
        newer = sync.incremental_sync_macro(provider(), ["interest_rate"], as_of=AS_OF)
        assert newer is not None and newer.version == "2026-07-10"
        assert sync.watermark(MACRO_DATASET) == date(2026, 7, 10)

    def test_fundamentals_and_fx(self, sync: ProviderSyncService) -> None:
        fundamentals = sync.sync_fundamentals(
            provider(), ["AAA", "BBB"], date(2026, 7, 10), as_of=AS_OF
        )
        assert fundamentals.dataset_id == FUNDAMENTALS_DATASET
        assert fundamentals.status is DatasetStatus.PUBLISHED
        fx = sync.sync_fx(provider(), ["USDVND", "EURVND"], date(2026, 7, 10), as_of=AS_OF)
        assert fx.dataset_id == FX_DATASET
        assert fx.quality.row_count == 1  # EURVND unknown upstream, skipped
        with pytest.raises(SyncError):
            sync.sync_fx(provider(), ["EURVND"], date(2026, 7, 10), as_of=AS_OF)


class TestPublishedPriceFacts:
    def test_facts_for_priced_day(
        self, sync: ProviderSyncService, pipeline: DataPipelineUseCases
    ) -> None:
        sync.full_sync_prices(
            provider(), ["AAA", "BBB"], date(2026, 7, 8), date(2026, 7, 10), as_of=AS_OF
        )
        facts = PublishedPriceFacts.from_pipeline(
            pipeline, classifications={"AAA": ("Materials", "Steel")}
        )
        on_day = facts(date(2026, 7, 9), "AAA")
        assert on_day["Feature.price.close"] == Decimal("10.75")
        assert on_day["Feature.price.volume"] == Decimal("1000")
        assert on_day["Company.Sector"] == "Materials"
        assert on_day["Company.Industry"] == "Steel"

    def test_missing_day_yields_no_price_facts(
        self, sync: ProviderSyncService, pipeline: DataPipelineUseCases
    ) -> None:
        sync.full_sync_prices(
            provider(), ["AAA", "BBB"], date(2026, 7, 8), date(2026, 7, 10), as_of=AS_OF
        )
        facts = PublishedPriceFacts.from_pipeline(pipeline)
        off_day = facts(date(2026, 7, 8), "BBB")  # BBB not priced on the 8th
        assert off_day == {"Company.Ticker": "BBB"}
        # BBB's 7-09 bar has no volume: close fact only
        on_day = facts(date(2026, 7, 9), "BBB")
        assert on_day["Feature.price.close"] == Decimal("20")
        assert "Feature.price.volume" not in on_day


@pytest.fixture()
def graph() -> KnowledgeGraphUseCases:
    engine = create_engine(
        "sqlite+pysqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    store = SqlGraphStore(sessionmaker(bind=engine, expire_on_commit=False, class_=Session))
    return KnowledgeGraphUseCases(store=store)


class TestKnowledgeSync:
    def test_materializes_company_industry_sector_chain(
        self, graph: KnowledgeGraphUseCases
    ) -> None:
        service = KnowledgeSyncService(graph=graph, provider=provider())
        synced = service.sync_companies(["BBB", "AAA", "ZZZ"])
        assert synced == ("AAA", "BBB")  # ZZZ unknown upstream, skipped

        snapshot = graph.snapshot()
        assert snapshot.nodes["company.AAA"].attributes["exchange"] == "HOSE"
        assert graph.neighbors("company.AAA") == ("industry.Steel",)
        assert graph.impacts("company.AAA") == ("industry.Steel", "sector.Materials")

    def test_sync_is_idempotent(self, graph: KnowledgeGraphUseCases) -> None:
        service = KnowledgeSyncService(graph=graph, provider=provider())
        service.sync_companies(["AAA", "BBB"])
        version = graph.snapshot().version
        service.sync_companies(["AAA", "BBB"])
        assert graph.snapshot().version == version
