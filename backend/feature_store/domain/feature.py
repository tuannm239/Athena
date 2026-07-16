"""Feature metadata and lifecycle (RFC-0023 §4–§8).

Lifecycle: Draft → Validated → Published → Deprecated → Archived.
Published features are immutable; publication requires documentation,
tests, a benchmark dataset, an owner and a version (RFC-0023 §7).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from enum import StrEnum

from shared_kernel.exceptions import DomainError

_SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


class FeatureLifecycleError(DomainError):
    """Raised on illegal lifecycle transitions or publication-gate failures."""


class FeatureStatus(StrEnum):
    DRAFT = "DRAFT"
    VALIDATED = "VALIDATED"
    PUBLISHED = "PUBLISHED"
    DEPRECATED = "DEPRECATED"
    ARCHIVED = "ARCHIVED"


_ALLOWED: dict[FeatureStatus, frozenset[FeatureStatus]] = {
    FeatureStatus.DRAFT: frozenset({FeatureStatus.VALIDATED}),
    FeatureStatus.VALIDATED: frozenset({FeatureStatus.PUBLISHED}),
    FeatureStatus.PUBLISHED: frozenset({FeatureStatus.DEPRECATED}),
    FeatureStatus.DEPRECATED: frozenset({FeatureStatus.ARCHIVED}),
    FeatureStatus.ARCHIVED: frozenset(),
}


class FactorCategory(StrEnum):
    """Factor categories (SPEC-06); features outside the factor library use OTHER."""

    QUALITY = "QUALITY"
    GROWTH = "GROWTH"
    VALUE = "VALUE"
    MOMENTUM = "MOMENTUM"
    LIQUIDITY = "LIQUIDITY"
    RISK = "RISK"
    GOVERNANCE = "GOVERNANCE"
    MARKET = "MARKET"
    PORTFOLIO = "PORTFOLIO"
    BEHAVIORAL = "BEHAVIORAL"
    OTHER = "OTHER"


@dataclass(frozen=True, slots=True)
class FeatureMetadata:
    """RFC-0023 §4 metadata; benchmark/test references gate publication (§7)."""

    feature_id: str
    name: str
    version: str
    owner: str
    description: str
    data_type: str
    unit: str
    calculation_method: str
    category: FactorCategory = FactorCategory.OTHER
    dependencies: tuple[str, ...] = ()
    freshness_policy: str = ""
    benchmark_dataset: str = ""
    test_suite: str = ""

    def __post_init__(self) -> None:
        for attr in ("feature_id", "name", "owner", "data_type", "calculation_method"):
            if not getattr(self, attr):
                raise ValueError(f"feature metadata requires {attr}")
        if not _SEMVER.match(self.version):
            raise ValueError(f"version must be MAJOR.MINOR.PATCH, got {self.version!r}")


@dataclass(frozen=True, slots=True)
class Feature:
    """A registered feature version moving through the RFC-0023 lifecycle."""

    metadata: FeatureMetadata
    status: FeatureStatus = FeatureStatus.DRAFT
    registered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def _transition(self, target: FeatureStatus) -> Feature:
        if target not in _ALLOWED[self.status]:
            raise FeatureLifecycleError(f"{self.status} -> {target} is not allowed")
        return replace(self, status=target)

    def validated(self) -> Feature:
        return self._transition(FeatureStatus.VALIDATED)

    def published(self) -> Feature:
        """Publish — enforces RFC-0023 §7 gates; published features are immutable."""
        missing = [
            gate
            for gate, value in (
                ("documentation", self.metadata.description),
                ("unit tests", self.metadata.test_suite),
                ("benchmark dataset", self.metadata.benchmark_dataset),
                ("owner", self.metadata.owner),
            )
            if not value
        ]
        if missing:
            raise FeatureLifecycleError(f"cannot publish without: {', '.join(missing)}")
        return self._transition(FeatureStatus.PUBLISHED)

    def deprecated(self) -> Feature:
        return self._transition(FeatureStatus.DEPRECATED)

    def archived(self) -> Feature:
        return self._transition(FeatureStatus.ARCHIVED)
