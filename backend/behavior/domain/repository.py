"""Decision journal port (SPEC-12: journal entries are immutable)."""

from __future__ import annotations

from abc import ABC, abstractmethod

from behavior.domain.journal import DecisionJournalEntry
from shared_kernel.identifiers import DecisionId


class JournalRepository(ABC):
    @abstractmethod
    def append(self, entry: DecisionJournalEntry) -> None:
        """Insert-only; historical records are never modified (SPEC-12)."""

    @abstractmethod
    def for_decision(self, decision_id: DecisionId) -> tuple[DecisionJournalEntry, ...]: ...

    @abstractmethod
    def all_entries(self) -> tuple[DecisionJournalEntry, ...]: ...
