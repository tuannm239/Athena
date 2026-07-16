"""SQL implementation of the DatasetCatalog port (RFC-0024 §7)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from data_pipeline.domain.dataset import (
    DatasetStatus,
    DatasetVersion,
    Lineage,
    QualityReport,
)
from data_pipeline.domain.repository import DatasetCatalog
from infrastructure.db.engine import session_scope
from infrastructure.db.models import DatasetRow
from shared_kernel.exceptions import NotFoundError


def _lineage_to_json(lineage: Lineage) -> dict[str, Any]:
    return {
        "source": lineage.source,
        "ingestion_time": lineage.ingestion_time.isoformat(),
        "pipeline_version": lineage.pipeline_version,
        "transformation_steps": list(lineage.transformation_steps),
        "dataset_version": lineage.dataset_version,
    }


def _quality_to_json(quality: QualityReport) -> dict[str, Any]:
    return {
        "completeness": str(quality.completeness),
        "accuracy": str(quality.accuracy),
        "freshness": str(quality.freshness),
        "consistency": str(quality.consistency),
        "uniqueness": str(quality.uniqueness),
        "row_count": quality.row_count,
        "quarantined_rows": quality.quarantined_rows,
    }


def _from_row(row: DatasetRow) -> DatasetVersion:
    lineage = row.lineage
    quality = row.quality
    return DatasetVersion(
        dataset_id=row.dataset_id,
        version=row.version,
        snapshot_id=row.snapshot_id,
        status=DatasetStatus(row.status),
        lineage=Lineage(
            source=lineage["source"],
            ingestion_time=datetime.fromisoformat(lineage["ingestion_time"]),
            pipeline_version=lineage["pipeline_version"],
            transformation_steps=tuple(lineage["transformation_steps"]),
            dataset_version=lineage["dataset_version"],
        ),
        quality=QualityReport(
            completeness=Decimal(quality["completeness"]),
            accuracy=Decimal(quality["accuracy"]),
            freshness=Decimal(quality["freshness"]),
            consistency=Decimal(quality["consistency"]),
            uniqueness=Decimal(quality["uniqueness"]),
            row_count=int(quality["row_count"]),
            quarantined_rows=int(quality["quarantined_rows"]),
        ),
        created_at=row.created_at,
    )


class SqlDatasetCatalog(DatasetCatalog):
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._sessions = session_factory

    def save(self, dataset: DatasetVersion) -> None:
        with session_scope(self._sessions) as session:
            session.add(
                DatasetRow(
                    dataset_id=dataset.dataset_id,
                    version=dataset.version,
                    snapshot_id=dataset.snapshot_id,
                    status=dataset.status.value,
                    lineage=_lineage_to_json(dataset.lineage),
                    quality=_quality_to_json(dataset.quality),
                    created_at=dataset.created_at,
                )
            )

    def get(self, dataset_id: str, version: str) -> DatasetVersion | None:
        with session_scope(self._sessions) as session:
            row = session.scalar(
                select(DatasetRow).where(
                    DatasetRow.dataset_id == dataset_id, DatasetRow.version == version
                )
            )
            return None if row is None else _from_row(row)

    def latest(
        self, dataset_id: str, *, status: DatasetStatus | None = None
    ) -> DatasetVersion | None:
        with session_scope(self._sessions) as session:
            query = (
                select(DatasetRow)
                .where(DatasetRow.dataset_id == dataset_id)
                .order_by(DatasetRow.created_at.desc())
            )
            if status is not None:
                query = query.where(DatasetRow.status == status.value)
            row = session.scalar(query.limit(1))
            return None if row is None else _from_row(row)

    def versions(self, dataset_id: str) -> tuple[DatasetVersion, ...]:
        with session_scope(self._sessions) as session:
            rows = session.scalars(
                select(DatasetRow)
                .where(DatasetRow.dataset_id == dataset_id)
                .order_by(DatasetRow.created_at)
            ).all()
            return tuple(_from_row(r) for r in rows)

    def set_status(self, dataset_id: str, version: str, status: DatasetStatus) -> None:
        with session_scope(self._sessions) as session:
            row = session.scalar(
                select(DatasetRow).where(
                    DatasetRow.dataset_id == dataset_id, DatasetRow.version == version
                )
            )
            if row is None:
                raise NotFoundError(f"dataset not found: {dataset_id}@{version}")
            row.status = status.value
