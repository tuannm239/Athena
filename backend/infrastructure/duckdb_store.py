"""DuckDB snapshot store (SPEC-07, DuckDB; SPEC-04 reproducibility).

Snapshots are immutable: a (snapshot_id, table) pair can be written once
and never overwritten. Reads of the same pair always return identical
data, which is the reproducibility guarantee analytical work relies on.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import polars as pl


class SnapshotImmutabilityError(RuntimeError):
    """Raised on any attempt to overwrite a published snapshot table."""


class DuckDbSnapshotStore:
    """Stores immutable, versioned analytical datasets as DuckDB files."""

    def __init__(self, directory: str | Path) -> None:
        self._dir = Path(directory)
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, snapshot_id: str) -> Path:
        if not snapshot_id or "/" in snapshot_id:
            raise ValueError(f"invalid snapshot id: {snapshot_id!r}")
        return self._dir / f"{snapshot_id}.duckdb"

    def write(self, snapshot_id: str, table: str, frame: pl.DataFrame) -> None:
        """Persist a dataset under (snapshot_id, table); overwriting is forbidden."""
        path = self._path(snapshot_id)
        with duckdb.connect(str(path)) as conn:
            exists = conn.execute(
                "SELECT count(*) FROM information_schema.tables WHERE table_name = ?",
                [table],
            ).fetchone()
            if exists is not None and int(exists[0]) > 0:
                raise SnapshotImmutabilityError(f"{snapshot_id}/{table} is already published")
            conn.register("_incoming", frame)
            conn.execute(f'CREATE TABLE "{table}" AS SELECT * FROM _incoming')

    def read(self, snapshot_id: str, table: str) -> pl.DataFrame:
        """Read a dataset back; identical inputs return identical frames."""
        path = self._path(snapshot_id)
        if not path.exists():
            raise FileNotFoundError(f"snapshot {snapshot_id} does not exist")
        with duckdb.connect(str(path), read_only=True) as conn:
            return conn.execute(f'SELECT * FROM "{table}"').pl()

    def tables(self, snapshot_id: str) -> tuple[str, ...]:
        path = self._path(snapshot_id)
        if not path.exists():
            return ()
        with duckdb.connect(str(path), read_only=True) as conn:
            rows = conn.execute(
                "SELECT table_name FROM information_schema.tables ORDER BY table_name"
            ).fetchall()
        return tuple(str(r[0]) for r in rows)
