"""Pipeline public interfaces (RFC-0024 §9): RunPipeline, ValidateDataset,
PublishDataset, RollbackDataset, GenerateQualityReport.

Datasets are persisted as immutable DuckDB snapshots; only runs whose
quality report passes may be published (RFC-0024 acceptance criteria).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

import polars as pl

from data_pipeline.domain.dataset import (
    DatasetSchema,
    DatasetStatus,
    DatasetVersion,
    Lineage,
    QualityReport,
)
from data_pipeline.domain.errors import DuplicateDatasetError, PublishError
from data_pipeline.domain.repository import DatasetCatalog
from data_pipeline.domain.stages import ingest, normalize, quality_report, validate
from shared_kernel.exceptions import NotFoundError

PIPELINE_VERSION = "1.0.0"


class SnapshotWriter(Protocol):
    """Port over the immutable snapshot store (implemented by DuckDbSnapshotStore)."""

    def write(self, snapshot_id: str, table: str, frame: pl.DataFrame) -> None: ...

    def read(self, snapshot_id: str, table: str) -> pl.DataFrame: ...


@dataclass
class DataPipelineUseCases:
    catalog: DatasetCatalog
    snapshots: SnapshotWriter

    def validate_dataset(
        self, frame: pl.DataFrame, schema: DatasetSchema, as_of: datetime | None = None
    ) -> QualityReport:
        """ValidateDataset(): run stages without persisting anything."""
        at = as_of or datetime.now(timezone.utc)
        source = ingest(frame, schema)
        result = validate(source, schema, at)
        return quality_report(source.height, result, schema, at)

    def run_pipeline(
        self,
        *,
        dataset_id: str,
        version: str,
        source: str,
        frame: pl.DataFrame,
        schema: DatasetSchema,
        as_of: datetime | None = None,
    ) -> DatasetVersion:
        """RunPipeline(): ingest → validate → normalize → quality → persist.

        The run is recorded as QUARANTINED unless its quality report passes,
        in which case it is PUBLISHED. Re-running an existing (id, version)
        raises DP003.
        """
        if self.catalog.get(dataset_id, version) is not None:
            raise DuplicateDatasetError(f"dataset already exists: {dataset_id}@{version}")
        at = as_of or datetime.now(timezone.utc)

        raw = ingest(frame, schema)
        result = validate(raw, schema, at)
        normalized = normalize(result.valid, schema)
        report = quality_report(raw.height, result, schema, at)

        snapshot_id = f"{dataset_id}-{version}"
        self.snapshots.write(snapshot_id, "data", normalized)
        if result.quarantined.height > 0:
            self.snapshots.write(snapshot_id, "quarantine", result.quarantined)

        dataset = DatasetVersion(
            dataset_id=dataset_id,
            version=version,
            snapshot_id=snapshot_id,
            status=DatasetStatus.PUBLISHED if report.passed else DatasetStatus.QUARANTINED,
            lineage=Lineage(
                source=source,
                ingestion_time=at,
                pipeline_version=PIPELINE_VERSION,
                transformation_steps=("ingest", *result.steps, "normalize", "quality"),
                dataset_version=version,
            ),
            quality=report,
        )
        self.catalog.save(dataset)
        return dataset

    def publish_dataset(self, dataset_id: str, version: str) -> DatasetVersion:
        """PublishDataset(): promote a quarantined run only if its report passed."""
        dataset = self.catalog.get(dataset_id, version)
        if dataset is None:
            raise NotFoundError(f"dataset not found: {dataset_id}@{version}")
        if not dataset.quality.passed:
            raise PublishError(f"quality gate failed for {dataset_id}@{version}; cannot publish")
        self.catalog.set_status(dataset_id, version, DatasetStatus.PUBLISHED)
        updated = self.catalog.get(dataset_id, version)
        assert updated is not None
        return updated

    def rollback_dataset(self, dataset_id: str, version: str) -> DatasetVersion | None:
        """RollbackDataset(): retire a published version; returns the new latest."""
        dataset = self.catalog.get(dataset_id, version)
        if dataset is None:
            raise NotFoundError(f"dataset not found: {dataset_id}@{version}")
        self.catalog.set_status(dataset_id, version, DatasetStatus.ROLLED_BACK)
        return self.catalog.latest(dataset_id, status=DatasetStatus.PUBLISHED)

    def generate_quality_report(self, dataset_id: str, version: str) -> QualityReport:
        """GenerateQualityReport(): the report persisted with the run."""
        dataset = self.catalog.get(dataset_id, version)
        if dataset is None:
            raise NotFoundError(f"dataset not found: {dataset_id}@{version}")
        return dataset.quality

    def read_published(self, dataset_id: str) -> pl.DataFrame:
        """Data of the latest published version (feature-store facing)."""
        latest = self.catalog.latest(dataset_id, status=DatasetStatus.PUBLISHED)
        if latest is None:
            raise NotFoundError(f"no published version of {dataset_id}")
        return self.snapshots.read(latest.snapshot_id, "data")
