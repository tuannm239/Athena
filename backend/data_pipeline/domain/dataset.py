"""Dataset versions, schemas, lineage and quality (RFC-0024 §5–§7).

Metric definitions (documented interpretations of RFC-0024 §6):
- completeness: 1 − null fraction over required columns
- uniqueness: 1 − duplicate-key fraction
- freshness: 1 if newest timestamp within the declared max age, else 0
- consistency: fraction of rows passing schema/timestamp validation
- accuracy: fraction of rows not quarantined by any rule
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum


class DatasetStatus(StrEnum):
    QUARANTINED = "QUARANTINED"
    PUBLISHED = "PUBLISHED"
    ROLLED_BACK = "ROLLED_BACK"


@dataclass(frozen=True, slots=True)
class DatasetSchema:
    """Declared contract a source must satisfy (RFC-0024 §5)."""

    required_columns: tuple[str, ...]
    key_columns: tuple[str, ...]
    timestamp_column: str | None = None
    max_age_days: int | None = None

    def __post_init__(self) -> None:
        if not self.required_columns:
            raise ValueError("schema requires at least one required column")
        missing_keys = set(self.key_columns) - set(self.required_columns)
        if missing_keys:
            raise ValueError(f"key columns must be required columns: {missing_keys}")


@dataclass(frozen=True, slots=True)
class Lineage:
    """Record-level provenance (RFC-0024 §7)."""

    source: str
    ingestion_time: datetime
    pipeline_version: str
    transformation_steps: tuple[str, ...]
    dataset_version: str

    def __post_init__(self) -> None:
        if not self.source:
            raise ValueError("lineage requires a source")


@dataclass(frozen=True, slots=True)
class QualityReport:
    """Published with every pipeline execution (RFC-0024 §6)."""

    completeness: Decimal
    accuracy: Decimal
    freshness: Decimal
    consistency: Decimal
    uniqueness: Decimal
    row_count: int
    quarantined_rows: int

    @property
    def passed(self) -> bool:
        """A dataset passes when nothing was quarantined and data is fresh."""
        return self.quarantined_rows == 0 and self.freshness == Decimal(1)


@dataclass(frozen=True, slots=True)
class DatasetVersion:
    dataset_id: str
    version: str
    snapshot_id: str
    status: DatasetStatus
    lineage: Lineage
    quality: QualityReport
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
