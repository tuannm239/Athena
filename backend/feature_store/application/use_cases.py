"""Feature Store use cases (RFC-0023 §5–§7; SPEC-06 §Registration)."""

from __future__ import annotations

from dataclasses import dataclass

from feature_store.domain.factor_catalogue import canonical_factors
from feature_store.domain.feature import Feature, FeatureMetadata
from feature_store.domain.repository import FeatureRegistry
from shared_kernel.exceptions import ConflictError, NotFoundError


@dataclass
class FeatureStoreUseCases:
    registry: FeatureRegistry

    def register(self, metadata: FeatureMetadata) -> Feature:
        """Register a new draft feature version (SPEC-06: duplicate ids rejected)."""
        if self.registry.get_version(metadata.feature_id, metadata.version) is not None:
            raise ConflictError(
                f"feature already registered: {metadata.feature_id}@{metadata.version}"
            )
        feature = Feature(metadata=metadata)
        self.registry.save(feature)
        return feature

    def _get(self, feature_id: str, version: str) -> Feature:
        feature = self.registry.get_version(feature_id, version)
        if feature is None:
            raise NotFoundError(f"feature not found: {feature_id}@{version}")
        return feature

    def validate(self, feature_id: str, version: str) -> Feature:
        feature = self._get(feature_id, version).validated()
        self.registry.save(feature)
        return feature

    def publish(self, feature_id: str, version: str) -> Feature:
        feature = self._get(feature_id, version).published()
        self.registry.save(feature)
        return feature

    def deprecate(self, feature_id: str, version: str) -> Feature:
        feature = self._get(feature_id, version).deprecated()
        self.registry.save(feature)
        return feature

    def archive(self, feature_id: str, version: str) -> Feature:
        feature = self._get(feature_id, version).archived()
        self.registry.save(feature)
        return feature

    # -- read APIs (RFC-0023 §6) ------------------------------------------

    def get_feature(self, feature_id: str) -> Feature:
        feature = self.registry.get(feature_id)
        if feature is None:
            raise NotFoundError(f"feature not found: {feature_id}")
        return feature

    def get_feature_version(self, feature_id: str, version: str) -> Feature:
        return self._get(feature_id, version)

    def list_features(self) -> tuple[Feature, ...]:
        return self.registry.list()

    def search_features(self, query: str) -> tuple[Feature, ...]:
        return self.registry.search(query)

    def seed_factor_catalogue(self) -> tuple[Feature, ...]:
        """Register any SPEC-06 factors not yet present (idempotent)."""
        registered: list[Feature] = []
        for metadata in canonical_factors():
            if self.registry.get_version(metadata.feature_id, metadata.version) is None:
                registered.append(self.register(metadata))
        return tuple(registered)
