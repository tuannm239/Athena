"""Unit tests — Data Pipeline stages and quality metrics (RFC-0024)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import polars as pl
import pytest

from data_pipeline.domain.dataset import DatasetSchema
from data_pipeline.domain.errors import InvalidSourceError, SchemaValidationError
from data_pipeline.domain.stages import ingest, normalize, quality_report, validate

AS_OF = datetime(2026, 7, 15, tzinfo=timezone.utc)


def schema() -> DatasetSchema:
    return DatasetSchema(
        required_columns=("ticker", "close", "as_of"),
        key_columns=("ticker", "as_of"),
        timestamp_column="as_of",
        max_age_days=7,
    )


def frame(rows: list[dict[str, object]]) -> pl.DataFrame:
    return pl.DataFrame(
        rows, schema={"ticker": pl.Utf8, "close": pl.Float64, "as_of": pl.Datetime("us", "UTC")}
    )


def good_rows() -> list[dict[str, object]]:
    return [
        {"ticker": "BBB", "close": 20.0, "as_of": AS_OF - timedelta(days=1)},
        {"ticker": "AAA", "close": 10.0, "as_of": AS_OF - timedelta(days=1)},
    ]


class TestStages:
    def test_ingest_rejects_empty_source(self) -> None:
        with pytest.raises(InvalidSourceError):
            ingest(pl.DataFrame(), schema())

    def test_missing_required_column_is_dp002(self) -> None:
        with pytest.raises(SchemaValidationError):
            validate(pl.DataFrame({"ticker": ["AAA"]}), schema(), AS_OF)

    def test_valid_rows_pass_and_are_normalized(self) -> None:
        result = validate(frame(good_rows()), schema(), AS_OF)
        assert result.quarantined.height == 0
        ordered = normalize(result.valid, schema())
        assert ordered["ticker"].to_list() == ["AAA", "BBB"]

    def test_nulls_duplicates_and_future_timestamps_quarantined(self) -> None:
        rows = good_rows() + [
            {"ticker": None, "close": 1.0, "as_of": AS_OF - timedelta(days=1)},
            {"ticker": "AAA", "close": 10.5, "as_of": AS_OF - timedelta(days=1)},  # dup key
            {"ticker": "CCC", "close": 3.0, "as_of": AS_OF + timedelta(days=1)},  # future
        ]
        result = validate(frame(rows), schema(), AS_OF)
        assert result.quarantined.height == 4  # dup counts both occurrences
        reasons = "".join(result.quarantined["_quarantine_reason"].to_list())
        assert "missing:ticker" in reasons
        assert "duplicate-key" in reasons
        assert "invalid-timestamp" in reasons


class TestQualityReport:
    def test_clean_data_passes(self) -> None:
        result = validate(frame(good_rows()), schema(), AS_OF)
        report = quality_report(2, result, schema(), AS_OF)
        assert report.passed
        assert report.completeness == Decimal(1)
        assert report.uniqueness == Decimal(1)

    def test_quarantine_fails_the_gate(self) -> None:
        rows = good_rows() + [{"ticker": None, "close": 1.0, "as_of": AS_OF - timedelta(days=1)}]
        result = validate(frame(rows), schema(), AS_OF)
        report = quality_report(3, result, schema(), AS_OF)
        assert not report.passed
        assert report.accuracy == Decimal(2) / Decimal(3)

    def test_stale_data_fails_freshness(self) -> None:
        rows = [{"ticker": "AAA", "close": 10.0, "as_of": AS_OF - timedelta(days=30)}]
        result = validate(frame(rows), schema(), AS_OF)
        report = quality_report(1, result, schema(), AS_OF)
        assert report.freshness == Decimal(0)
        assert not report.passed
