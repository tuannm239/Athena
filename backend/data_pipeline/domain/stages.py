"""Deterministic pipeline stages (RFC-0024 §4–§5).

Ingestion → Validation → Normalization → Enrichment → Quality Checks.
Invalid records are quarantined, never silently dropped or published.
All transformations are pure functions of their inputs.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import polars as pl

from data_pipeline.domain.dataset import DatasetSchema, QualityReport
from data_pipeline.domain.errors import InvalidSourceError, SchemaValidationError


@dataclass(frozen=True, slots=True)
class StageResult:
    """Valid rows plus quarantined rows with their rejection reasons."""

    valid: pl.DataFrame
    quarantined: pl.DataFrame
    steps: tuple[str, ...]


def ingest(frame: pl.DataFrame, schema: DatasetSchema) -> pl.DataFrame:
    """Ingestion: accept the raw frame; reject empty or column-less sources (DP001)."""
    if frame.width == 0:
        raise InvalidSourceError("source has no columns")
    return frame


def validate(frame: pl.DataFrame, schema: DatasetSchema, as_of: datetime) -> StageResult:
    """Validation (RFC-0024 §5): schema, duplicates, missing values, timestamps."""
    missing_columns = [c for c in schema.required_columns if c not in frame.columns]
    if missing_columns:
        raise SchemaValidationError(f"missing required columns: {missing_columns}")

    reasons = pl.lit("")
    for column in schema.required_columns:
        reasons = (
            pl.when(pl.col(column).is_null())
            .then(reasons + pl.lit(f"missing:{column};"))
            .otherwise(reasons)
        )
    if schema.key_columns:
        duplicate = pl.struct(list(schema.key_columns)).is_duplicated()
        reasons = pl.when(duplicate).then(reasons + pl.lit("duplicate-key;")).otherwise(reasons)
    if schema.timestamp_column is not None:
        future = pl.col(schema.timestamp_column) > pl.lit(as_of)
        reasons = (
            pl.when(future.fill_null(True))
            .then(reasons + pl.lit("invalid-timestamp;"))
            .otherwise(reasons)
        )

    annotated = frame.with_columns(reasons.alias("_quarantine_reason"))
    valid = annotated.filter(pl.col("_quarantine_reason") == "").drop("_quarantine_reason")
    quarantined = annotated.filter(pl.col("_quarantine_reason") != "")
    return StageResult(valid=valid, quarantined=quarantined, steps=("validate",))


def normalize(frame: pl.DataFrame, schema: DatasetSchema) -> pl.DataFrame:
    """Normalization: deterministic ordering by key (and timestamp) columns."""
    order = list(schema.key_columns) or list(schema.required_columns)
    if schema.timestamp_column is not None and schema.timestamp_column not in order:
        order.append(schema.timestamp_column)
    return frame.sort(order)


def quality_report(
    source_rows: int,
    result: StageResult,
    schema: DatasetSchema,
    as_of: datetime,
) -> QualityReport:
    """Quality checks (RFC-0024 §6) over the validated output."""
    valid = result.valid
    quarantined = result.quarantined.height
    total = source_rows if source_rows > 0 else 1

    null_cells = sum(valid[c].null_count() for c in schema.required_columns)
    cells = max(valid.height * len(schema.required_columns), 1)
    completeness = Decimal(cells - null_cells) / Decimal(cells)

    if schema.key_columns and valid.height > 0:
        unique_rows = valid.select(schema.key_columns).unique().height
        uniqueness = Decimal(unique_rows) / Decimal(valid.height)
    else:
        uniqueness = Decimal(1)

    freshness = Decimal(1)
    if schema.timestamp_column is not None and schema.max_age_days is not None:
        if valid.height == 0:
            freshness = Decimal(0)
        else:
            newest = valid[schema.timestamp_column].max()
            assert isinstance(newest, datetime)
            if newest.tzinfo is None:
                newest = newest.replace(tzinfo=timezone.utc)
            limit = as_of - timedelta(days=schema.max_age_days)
            freshness = Decimal(1) if newest >= limit else Decimal(0)

    consistency = Decimal(valid.height) / Decimal(total)
    accuracy = Decimal(total - quarantined) / Decimal(total)

    return QualityReport(
        completeness=completeness,
        accuracy=accuracy,
        freshness=freshness,
        consistency=consistency,
        uniqueness=uniqueness,
        row_count=valid.height,
        quarantined_rows=quarantined,
    )
