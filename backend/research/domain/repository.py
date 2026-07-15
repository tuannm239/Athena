"""Research repository interface (SPEC-03, Repository Interfaces)."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from research.domain.research_summary import ResearchSummary


class ResearchRepository(ABC):
    @abstractmethod
    def save(self, summary: ResearchSummary) -> None: ...

    @abstractmethod
    def get(self, summary_id: uuid.UUID) -> ResearchSummary | None: ...
