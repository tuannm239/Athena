"""Unit tests — Feature Store (RFC-0023) and Factor Library (SPEC-06)."""

from __future__ import annotations

import pytest

from feature_store.domain.factor_catalogue import canonical_factors
from feature_store.domain.feature import (
    FactorCategory,
    Feature,
    FeatureLifecycleError,
    FeatureMetadata,
    FeatureStatus,
)


def metadata(**overrides: str) -> FeatureMetadata:
    base: dict[str, str] = {
        "feature_id": "quality.roe",
        "name": "ROE",
        "version": "1.0.0",
        "owner": "factor-library",
        "description": "Return on equity",
        "data_type": "decimal",
        "unit": "ratio",
        "calculation_method": "net_income / avg_equity",
        "benchmark_dataset": "bench-2025Q4",
        "test_suite": "tests/factors/test_roe.py",
    }
    base.update(overrides)
    return FeatureMetadata(**base)  # type: ignore[arg-type]


class TestFeatureMetadata:
    def test_semver_enforced(self) -> None:
        with pytest.raises(ValueError):
            metadata(version="v1")

    def test_required_fields(self) -> None:
        with pytest.raises(ValueError):
            metadata(owner="")


class TestFeatureLifecycle:
    def test_full_lifecycle(self) -> None:
        feature = Feature(metadata=metadata())
        assert feature.status is FeatureStatus.DRAFT
        feature = feature.validated().published().deprecated().archived()
        assert feature.status is FeatureStatus.ARCHIVED

    def test_draft_cannot_publish_directly(self) -> None:
        with pytest.raises(FeatureLifecycleError):
            Feature(metadata=metadata()).published()

    def test_publication_gates(self) -> None:
        feature = Feature(metadata=metadata(benchmark_dataset="", test_suite="")).validated()
        with pytest.raises(FeatureLifecycleError) as excinfo:
            feature.published()
        assert "benchmark dataset" in str(excinfo.value)
        assert "unit tests" in str(excinfo.value)


class TestFactorCatalogue:
    def test_catalogue_covers_spec06_categories(self) -> None:
        factors = canonical_factors()
        categories = {f.category for f in factors}
        assert {
            FactorCategory.QUALITY,
            FactorCategory.GROWTH,
            FactorCategory.VALUE,
            FactorCategory.MOMENTUM,
            FactorCategory.LIQUIDITY,
            FactorCategory.RISK,
            FactorCategory.GOVERNANCE,
        } <= categories
        assert len({f.feature_id for f in factors}) == len(factors)

    def test_catalogue_counts_match_spec06(self) -> None:
        factors = canonical_factors()
        by_category: dict[FactorCategory, int] = {}
        for f in factors:
            by_category[f.category] = by_category.get(f.category, 0) + 1
        assert by_category[FactorCategory.QUALITY] == 5
        assert by_category[FactorCategory.GROWTH] == 4
        assert by_category[FactorCategory.VALUE] == 4
        assert by_category[FactorCategory.MOMENTUM] == 3
        assert by_category[FactorCategory.LIQUIDITY] == 3
        assert by_category[FactorCategory.RISK] == 4
        assert by_category[FactorCategory.GOVERNANCE] == 3
