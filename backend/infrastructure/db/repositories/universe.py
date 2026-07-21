"""SQL implementation of the investment-universe repository.

Persists the editable universe in `watchlist_universe`. The sync path reads
active symbols from here, so the universe is runtime-editable and never
hardcoded in business logic.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from data_pipeline.universe import SyncLevel, UniverseEntry, UniverseRepository
from infrastructure.db.engine import session_scope
from infrastructure.db.models import UniverseRow


def _from_row(row: UniverseRow) -> UniverseEntry:
    return UniverseEntry(
        symbol=row.symbol,
        sector=row.sector,
        sync_level=SyncLevel(row.sync_level),
        is_active=row.is_active,
    )


class SqlUniverseRepository(UniverseRepository):
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._sessions = session_factory

    def active_symbols(self, level: SyncLevel | None = None) -> tuple[str, ...]:
        with session_scope(self._sessions) as session:
            query = (
                select(UniverseRow.symbol)
                .where(UniverseRow.is_active.is_(True))
                .order_by(UniverseRow.priority, UniverseRow.symbol)
            )
            if level is not None:
                query = query.where(UniverseRow.sync_level == level.value)
            return tuple(str(s) for s in session.scalars(query).all())

    def all(self) -> tuple[UniverseEntry, ...]:
        with session_scope(self._sessions) as session:
            rows = session.scalars(
                select(UniverseRow).order_by(UniverseRow.priority, UniverseRow.symbol)
            ).all()
            return tuple(_from_row(r) for r in rows)

    def upsert(self, entry: UniverseEntry) -> None:
        with session_scope(self._sessions) as session:
            now = datetime.now(timezone.utc)
            row = session.scalar(select(UniverseRow).where(UniverseRow.symbol == entry.symbol))
            if row is None:
                session.add(
                    UniverseRow(
                        symbol=entry.symbol,
                        sector=entry.sector,
                        priority=entry.priority,
                        sync_level=entry.sync_level.value,
                        is_active=entry.is_active,
                        created_at=now,
                        updated_at=now,
                    )
                )
                return
            row.sector = entry.sector
            row.priority = entry.priority
            row.sync_level = entry.sync_level.value
            row.is_active = entry.is_active
            row.updated_at = now

    def set_active(self, symbol: str, active: bool) -> None:
        with session_scope(self._sessions) as session:
            row = session.scalar(select(UniverseRow).where(UniverseRow.symbol == symbol))
            if row is not None:
                row.is_active = active
                row.updated_at = datetime.now(timezone.utc)

    def seed_if_empty(self, entries: tuple[UniverseEntry, ...]) -> int:
        """Insert the seed universe only when the table is empty. Idempotent."""
        with session_scope(self._sessions) as session:
            existing = session.scalar(select(UniverseRow.id).limit(1))
            if existing is not None:
                return 0
            now = datetime.now(timezone.utc)
            session.add_all(
                UniverseRow(
                    symbol=e.symbol,
                    sector=e.sector,
                    priority=e.priority,
                    sync_level=e.sync_level.value,
                    is_active=e.is_active,
                    created_at=now,
                    updated_at=now,
                )
                for e in entries
            )
            return len(entries)
