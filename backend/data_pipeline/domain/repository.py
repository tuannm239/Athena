"""Dataset catalog port (RFC-0024 §7–§9)."""

from __future__ import annotations

from abc import ABC, abstractmethod

from data_pipeline.domain.dataset import DatasetStatus, DatasetVersion


class DatasetCatalog(ABC):
    @abstractmethod
    def save(self, dataset: DatasetVersion) -> None: ...

    @abstractmethod
    def get(self, dataset_id: str, version: str) -> DatasetVersion | None: ...

    @abstractmethod
    def latest(
        self, dataset_id: str, *, status: DatasetStatus | None = None
    ) -> DatasetVersion | None: ...

    @abstractmethod
    def versions(self, dataset_id: str) -> tuple[DatasetVersion, ...]: ...

    @abstractmethod
    def set_status(self, dataset_id: str, version: str, status: DatasetStatus) -> None: ...
