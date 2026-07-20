"""SQL snapshot store — durable backend for the immutable snapshot store.

Implements the same contract as `DuckDbSnapshotStore` (write / read / tables)
but persists each snapshot table in the relational database (Postgres/Neon) as
Parquet bytes, so published datasets survive restarts and ephemeral disks —
the DuckDB file-based store loses data whenever the local disk is reclaimed
(e.g. a free-tier container spin-down), which leaves the catalog pointing at a
"published" version whose data has vanished.

Same immutability guarantee: a (snapshot_id, table) pair is written once and
never overwritten.
"""

from __future__ import annotations

import io
from datetime import datetime, timezone

import polars as pl
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from infrastructure.config import Settings
from infrastructure.db.engine import session_scope
from infrastructure.db.models import SnapshotRow
from infrastructure.duckdb_store import DuckDbSnapshotStore, SnapshotImmutabilityError


class SqlSnapshotStore:
    """Stores immutable, versioned analytical datasets in the database."""

    def __init__(self, sessions: sessionmaker[Session]) -> None:
        self._sessions = sessions

    @staticmethod
    def _validate_id(snapshot_id: str) -> None:
        if not snapshot_id or "/" in snapshot_id:
            raise ValueError(f"invalid snapshot id: {snapshot_id!r}")

    def write(self, snapshot_id: str, table: str, frame: pl.DataFrame) -> None:
        """Persist a dataset under (snapshot_id, table); overwriting is forbidden."""
        self._validate_id(snapshot_id)
        buffer = io.BytesIO()
        frame.write_parquet(buffer)
        payload = buffer.getvalue()
        with session_scope(self._sessions) as session:
            existing = session.execute(
                select(SnapshotRow.id).where(
                    SnapshotRow.snapshot_id == snapshot_id,
                    SnapshotRow.table_name == table,
                )
            ).first()
            if existing is not None:
                raise SnapshotImmutabilityError(f"{snapshot_id}/{table} is already published")
            session.add(
                SnapshotRow(
                    snapshot_id=snapshot_id,
                    table_name=table,
                    data=payload,
                    created_at=datetime.now(timezone.utc),
                )
            )

    def read(self, snapshot_id: str, table: str) -> pl.DataFrame:
        """Read a dataset back; identical inputs return identical frames."""
        self._validate_id(snapshot_id)
        with session_scope(self._sessions) as session:
            row = session.execute(
                select(SnapshotRow.data).where(
                    SnapshotRow.snapshot_id == snapshot_id,
                    SnapshotRow.table_name == table,
                )
            ).first()
        if row is None:
            raise FileNotFoundError(f"snapshot {snapshot_id}/{table} does not exist")
        return pl.read_parquet(io.BytesIO(row[0]))

    def tables(self, snapshot_id: str) -> tuple[str, ...]:
        self._validate_id(snapshot_id)
        with session_scope(self._sessions) as session:
            rows = session.execute(
                select(SnapshotRow.table_name)
                .where(SnapshotRow.snapshot_id == snapshot_id)
                .order_by(SnapshotRow.table_name)
            ).all()
        return tuple(str(r[0]) for r in rows)


def build_snapshot_store(
    settings: Settings, sessions: sessionmaker[Session]
) -> SqlSnapshotStore | DuckDbSnapshotStore:
    """Pick the snapshot backend from settings (`SNAPSHOT_BACKEND`).

    Both the sync writer (CLI) and the API reader call this, so they always
    agree on where snapshots live. `sql` is durable across restarts; `duckdb`
    (default) is the fast local-file store.
    """
    if settings.snapshot_backend == "sql":
        return SqlSnapshotStore(sessions)
    return DuckDbSnapshotStore(settings.duckdb_dir)
