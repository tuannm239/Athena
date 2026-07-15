"""Decision repository interface (SPEC-03, Repository Interfaces).

Repositories are interfaces only; implementations belong to Infrastructure.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from decision_kernel.domain.decision import Decision
from shared_kernel.identifiers import DecisionId


class DecisionRepository(ABC):
    @abstractmethod
    def save(self, decision: Decision) -> None: ...

    @abstractmethod
    def get(self, decision_id: DecisionId) -> Decision | None: ...
