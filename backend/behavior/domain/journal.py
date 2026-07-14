"""Decision journal (SPEC-12, Decision Journal).

Journal entries are immutable; historical records cannot be modified
(SPEC-12, Business Rules). Every review references the original decision.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from shared_kernel.identifiers import DecisionId


@dataclass(frozen=True, slots=True)
class DecisionJournalEntry:
    decision_id: DecisionId
    original_hypothesis: str
    supporting_evidence: tuple[str, ...]
    counter_evidence: tuple[str, ...]
    expected_outcome: str
    actual_outcome: str = ""
    lessons_learned: str = ""
    recorded_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if not self.original_hypothesis:
            raise ValueError("journal entry requires the original hypothesis")
