"""SQL implementation of the FeatureRegistry port (RFC-0023).

Published feature versions are immutable: saving over a PUBLISHED row is
rejected unless the update is itself the lifecycle transition away from
PUBLISHED (deprecation), per RFC-0023 §5/§8.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from feature_store.domain.feature import (
    FactorCategory,
    Feature,
    FeatureLifecycleError,
    FeatureMetadata,
    FeatureStatus,
)
from feature_store.domain.repository import FeatureRegistry
from infrastructure.db.engine import session_scope
from infrastructure.db.models import FeatureDefinitionRow


def _metadata_to_json(metadata: FeatureMetadata) -> dict[str, Any]:
    return {
        "feature_id": metadata.feature_id,
        "name": metadata.name,
        "version": metadata.version,
        "owner": metadata.owner,
        "description": metadata.description,
        "data_type": metadata.data_type,
        "unit": metadata.unit,
        "calculation_method": metadata.calculation_method,
        "category": metadata.category.value,
        "dependencies": list(metadata.dependencies),
        "freshness_policy": metadata.freshness_policy,
        "benchmark_dataset": metadata.benchmark_dataset,
        "test_suite": metadata.test_suite,
    }


def _metadata_from_json(payload: dict[str, Any]) -> FeatureMetadata:
    return FeatureMetadata(
        feature_id=payload["feature_id"],
        name=payload["name"],
        version=payload["version"],
        owner=payload["owner"],
        description=payload["description"],
        data_type=payload["data_type"],
        unit=payload["unit"],
        calculation_method=payload["calculation_method"],
        category=FactorCategory(payload["category"]),
        dependencies=tuple(payload["dependencies"]),
        freshness_policy=payload["freshness_policy"],
        benchmark_dataset=payload["benchmark_dataset"],
        test_suite=payload["test_suite"],
    )


def _from_row(row: FeatureDefinitionRow) -> Feature:
    return Feature(
        metadata=_metadata_from_json(row.metadata_json),
        status=FeatureStatus(row.status),
        registered_at=row.registered_at,
    )


class SqlFeatureRegistry(FeatureRegistry):
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._sessions = session_factory

    def save(self, feature: Feature) -> None:
        with session_scope(self._sessions) as session:
            row = session.scalar(
                select(FeatureDefinitionRow).where(
                    FeatureDefinitionRow.feature_id == feature.metadata.feature_id,
                    FeatureDefinitionRow.version == feature.metadata.version,
                )
            )
            if row is None:
                session.add(
                    FeatureDefinitionRow(
                        feature_id=feature.metadata.feature_id,
                        version=feature.metadata.version,
                        status=feature.status.value,
                        metadata_json=_metadata_to_json(feature.metadata),
                        registered_at=feature.registered_at,
                    )
                )
                return
            if (
                row.status == FeatureStatus.PUBLISHED.value
                and feature.status is not FeatureStatus.DEPRECATED
            ):
                raise FeatureLifecycleError(
                    f"published feature is immutable: "
                    f"{feature.metadata.feature_id}@{feature.metadata.version}"
                )
            row.status = feature.status.value
            row.metadata_json = _metadata_to_json(feature.metadata)

    def get(self, feature_id: str) -> Feature | None:
        with session_scope(self._sessions) as session:
            row = session.scalar(
                select(FeatureDefinitionRow)
                .where(FeatureDefinitionRow.feature_id == feature_id)
                .order_by(FeatureDefinitionRow.registered_at.desc())
                .limit(1)
            )
            return None if row is None else _from_row(row)

    def get_version(self, feature_id: str, version: str) -> Feature | None:
        with session_scope(self._sessions) as session:
            row = session.scalar(
                select(FeatureDefinitionRow).where(
                    FeatureDefinitionRow.feature_id == feature_id,
                    FeatureDefinitionRow.version == version,
                )
            )
            return None if row is None else _from_row(row)

    def list(self) -> tuple[Feature, ...]:
        with session_scope(self._sessions) as session:
            rows = session.scalars(
                select(FeatureDefinitionRow).order_by(FeatureDefinitionRow.feature_id)
            ).all()
            return tuple(_from_row(r) for r in rows)

    def search(self, query: str) -> tuple[Feature, ...]:
        needle = query.lower()
        return tuple(
            f
            for f in self.list()
            if needle in f.metadata.feature_id.lower()
            or needle in f.metadata.name.lower()
            or needle in f.metadata.description.lower()
        )
