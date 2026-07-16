"""SQL implementation of the JournalRepository port (SPEC-12).

Insert-only by construction: no update or delete path exists.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from behavior.domain.journal import DecisionJournalEntry
from behavior.domain.repository import JournalRepository
from infrastructure.db.engine import session_scope
from infrastructure.db.models import JournalRow
from shared_kernel.identifiers import DecisionId


def _from_row(row: JournalRow) -> DecisionJournalEntry:
    return DecisionJournalEntry(
        decision_id=DecisionId(row.decision_id),
        original_hypothesis=row.original_hypothesis,
        supporting_evidence=tuple(row.supporting_evidence),
        counter_evidence=tuple(row.counter_evidence),
        expected_outcome=row.expected_outcome,
        actual_outcome=row.actual_outcome,
        lessons_learned=row.lessons_learned,
        recorded_at=row.recorded_at,
    )


class SqlJournalRepository(JournalRepository):
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._sessions = session_factory

    def append(self, entry: DecisionJournalEntry) -> None:
        with session_scope(self._sessions) as session:
            session.add(
                JournalRow(
                    decision_id=entry.decision_id.value,
                    original_hypothesis=entry.original_hypothesis,
                    supporting_evidence=list(entry.supporting_evidence),
                    counter_evidence=list(entry.counter_evidence),
                    expected_outcome=entry.expected_outcome,
                    actual_outcome=entry.actual_outcome,
                    lessons_learned=entry.lessons_learned,
                    recorded_at=entry.recorded_at,
                )
            )

    def for_decision(self, decision_id: DecisionId) -> tuple[DecisionJournalEntry, ...]:
        with session_scope(self._sessions) as session:
            rows = session.scalars(
                select(JournalRow)
                .where(JournalRow.decision_id == decision_id.value)
                .order_by(JournalRow.recorded_at)
            ).all()
            return tuple(_from_row(r) for r in rows)

    def all_entries(self) -> tuple[DecisionJournalEntry, ...]:
        with session_scope(self._sessions) as session:
            rows = session.scalars(select(JournalRow).order_by(JournalRow.recorded_at)).all()
            return tuple(_from_row(r) for r in rows)
