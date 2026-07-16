"""Feature registry port (RFC-0023 §6: read APIs; §5: immutability)."""

from __future__ import annotations

from abc import ABC, abstractmethod

from feature_store.domain.feature import Feature


class FeatureRegistry(ABC):
    @abstractmethod
    def save(self, feature: Feature) -> None:
        """Persist a feature version; overwriting a PUBLISHED version is forbidden."""

    @abstractmethod
    def get(self, feature_id: str) -> Feature | None:
        """Latest registered version of the feature."""

    @abstractmethod
    def get_version(self, feature_id: str, version: str) -> Feature | None: ...

    @abstractmethod
    def list(self) -> tuple[Feature, ...]: ...

    @abstractmethod
    def search(self, query: str) -> tuple[Feature, ...]:
        """Case-insensitive match on id, name and description."""
