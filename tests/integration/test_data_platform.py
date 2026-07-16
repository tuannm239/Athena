"""Integration tests — Feature Store registry + Data Pipeline end-to-end
(RFC-0023, RFC-0024) over SQLite and a temporary DuckDB snapshot store."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import polars as pl
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from data_pipeline.application.use_cases import DataPipelineUseCases
from data_pipeline.domain.dataset import DatasetSchema, DatasetStatus
from data_pipeline.domain.errors import DuplicateDatasetError, PublishError
from feature_store.application.use_cases import FeatureStoreUseCases
from feature_store.domain.feature import FeatureLifecycleError, FeatureStatus
from infrastructure.db.base import Base
from infrastructure.db.repositories.dataset_catalog import SqlDatasetCatalog
from infrastructure.db.repositories.feature_registry import SqlFeatureRegistry
from infrastructure.duckdb_store import DuckDbSnapshotStore
from shared_kernel.exceptions import ConflictError

AS_OF = datetime(2026, 7, 15, tzinfo=timezone.utc)


@pytest.fixture()
def sessions() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite+pysqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


class TestFeatureRegistry:
    def test_seed_catalogue_is_idempotent(self, sessions: sessionmaker[Session]) -> None:
        store = FeatureStoreUseCases(registry=SqlFeatureRegistry(sessions))
        first = store.seed_factor_catalogue()
        assert len(first) == 26
        assert store.seed_factor_catalogue() == ()
        assert len(store.list_features()) == 26

    def test_lifecycle_and_immutability(self, sessions: sessionmaker[Session]) -> None:
        store = FeatureStoreUseCases(registry=SqlFeatureRegistry(sessions))
        store.seed_factor_catalogue()
        with pytest.raises(ConflictError):
            store.register(store.get_feature("quality.roe").metadata)

        with pytest.raises(FeatureLifecycleError):
            store.publish("quality.roe", "1.0.0")  # draft: benchmark/tests missing

        store.validate("quality.roe", "1.0.0")
        with pytest.raises(FeatureLifecycleError):
            store.publish("quality.roe", "1.0.0")  # publication gates still unmet

    def test_search_and_versions(self, sessions: sessionmaker[Session]) -> None:
        store = FeatureStoreUseCases(registry=SqlFeatureRegistry(sessions))
        store.seed_factor_catalogue()
        hits = store.search_features("momentum")
        assert {f.metadata.feature_id for f in hits} >= {
            "momentum.relative_strength",
            "momentum.price",
            "momentum.volume",
        }
        assert store.get_feature_version("risk.beta", "1.0.0").status is FeatureStatus.DRAFT


class TestDataPipelineEndToEnd:
    def _pipeline(self, sessions: sessionmaker[Session], tmp_path: Path) -> DataPipelineUseCases:
        return DataPipelineUseCases(
            catalog=SqlDatasetCatalog(sessions),
            snapshots=DuckDbSnapshotStore(tmp_path),
        )

    def _schema(self) -> DatasetSchema:
        return DatasetSchema(
            required_columns=("ticker", "close", "as_of"),
            key_columns=("ticker", "as_of"),
            timestamp_column="as_of",
            max_age_days=7,
        )

    def _frame(self, extra: list[dict[str, object]] | None = None) -> pl.DataFrame:
        rows: list[dict[str, object]] = [
            {"ticker": "AAA", "close": 10.0, "as_of": AS_OF - timedelta(days=1)},
            {"ticker": "BBB", "close": 20.0, "as_of": AS_OF - timedelta(days=1)},
        ] + (extra or [])
        return pl.DataFrame(
            rows,
            schema={"ticker": pl.Utf8, "close": pl.Float64, "as_of": pl.Datetime("us", "UTC")},
        )

    def test_clean_run_publishes_with_lineage(
        self, sessions: sessionmaker[Session], tmp_path: Path
    ) -> None:
        pipeline = self._pipeline(sessions, tmp_path)
        dataset = pipeline.run_pipeline(
            dataset_id="prices.daily",
            version="2026.07.15",
            source="hose-eod",
            frame=self._frame(),
            schema=self._schema(),
            as_of=AS_OF,
        )
        assert dataset.status is DatasetStatus.PUBLISHED
        assert dataset.lineage.transformation_steps == (
            "ingest",
            "validate",
            "normalize",
            "quality",
        )
        published = pipeline.read_published("prices.daily")
        assert published["ticker"].to_list() == ["AAA", "BBB"]
        assert pipeline.generate_quality_report("prices.daily", "2026.07.15").passed

    def test_dirty_run_is_quarantined_and_cannot_publish(
        self, sessions: sessionmaker[Session], tmp_path: Path
    ) -> None:
        pipeline = self._pipeline(sessions, tmp_path)
        dirty = self._frame(
            extra=[{"ticker": None, "close": 1.0, "as_of": AS_OF - timedelta(days=1)}]
        )
        dataset = pipeline.run_pipeline(
            dataset_id="prices.daily",
            version="2026.07.15",
            source="hose-eod",
            frame=dirty,
            schema=self._schema(),
            as_of=AS_OF,
        )
        assert dataset.status is DatasetStatus.QUARANTINED
        with pytest.raises(PublishError):
            pipeline.publish_dataset("prices.daily", "2026.07.15")

    def test_duplicate_version_is_dp003(
        self, sessions: sessionmaker[Session], tmp_path: Path
    ) -> None:
        pipeline = self._pipeline(sessions, tmp_path)
        pipeline.run_pipeline(
            dataset_id="prices.daily",
            version="2026.07.15",
            source="hose-eod",
            frame=self._frame(),
            schema=self._schema(),
            as_of=AS_OF,
        )
        with pytest.raises(DuplicateDatasetError):
            pipeline.run_pipeline(
                dataset_id="prices.daily",
                version="2026.07.15",
                source="hose-eod",
                frame=self._frame(),
                schema=self._schema(),
                as_of=AS_OF,
            )

    def test_rollback_restores_previous_published(
        self, sessions: sessionmaker[Session], tmp_path: Path
    ) -> None:
        pipeline = self._pipeline(sessions, tmp_path)
        for version in ("2026.07.14", "2026.07.15"):
            pipeline.run_pipeline(
                dataset_id="prices.daily",
                version=version,
                source="hose-eod",
                frame=self._frame(),
                schema=self._schema(),
                as_of=AS_OF,
            )
        latest = pipeline.rollback_dataset("prices.daily", "2026.07.15")
        assert latest is not None and latest.version == "2026.07.14"
        assert pipeline.read_published("prices.daily").height == 2
