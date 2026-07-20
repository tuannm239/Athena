"""SQL snapshot store — durable snapshot backend (round-trip + immutability).

Uses an in-memory SQLite database (Base.metadata.create_all) so the store's
contract is verified without Postgres: write/read round-trip preserves the
frame, tables() lists what was written, immutability is enforced, and a second
store instance over the same DB reads back what the first wrote (the durability
property that the DuckDB file store loses on an ephemeral disk).
"""

from __future__ import annotations

import polars as pl
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from infrastructure.config import Settings
from infrastructure.db.base import Base
from infrastructure.duckdb_store import SnapshotImmutabilityError
from infrastructure.sql_snapshot_store import SqlSnapshotStore, build_snapshot_store


@pytest.fixture()
def sessions() -> sessionmaker:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def _frame() -> pl.DataFrame:
    return pl.DataFrame({"ticker": ["VNINDEX", "FPT"], "close": ["1293.11", "140.6"]})


class TestRoundTrip:
    def test_write_then_read_preserves_frame(self, sessions: sessionmaker) -> None:
        store = SqlSnapshotStore(sessions)
        store.write("snap1", "prices", _frame())
        back = store.read("snap1", "prices")
        assert back.sort("ticker").to_dicts() == _frame().sort("ticker").to_dicts()

    def test_tables_lists_written_tables(self, sessions: sessionmaker) -> None:
        store = SqlSnapshotStore(sessions)
        store.write("snap1", "prices", _frame())
        assert store.tables("snap1") == ("prices",)

    def test_missing_snapshot_raises_filenotfound(self, sessions: sessionmaker) -> None:
        with pytest.raises(FileNotFoundError):
            SqlSnapshotStore(sessions).read("nope", "prices")


class TestImmutability:
    def test_overwrite_forbidden(self, sessions: sessionmaker) -> None:
        store = SqlSnapshotStore(sessions)
        store.write("snap1", "prices", _frame())
        with pytest.raises(SnapshotImmutabilityError):
            store.write("snap1", "prices", _frame())


class TestDurability:
    def test_second_store_reads_first_writes(self, sessions: sessionmaker) -> None:
        # Two independent store instances over the same DB — models the sync
        # writer and the API reader as separate processes.
        SqlSnapshotStore(sessions).write("snap1", "prices", _frame())
        reader = SqlSnapshotStore(sessions)
        assert "VNINDEX" in set(reader.read("snap1", "prices")["ticker"].to_list())


class TestFactory:
    def test_sql_backend_selected(self, sessions: sessionmaker) -> None:
        cfg = Settings.from_env()
        object.__setattr__(cfg, "snapshot_backend", "sql")
        store = build_snapshot_store(cfg, sessions)
        assert isinstance(store, SqlSnapshotStore)

    def test_duckdb_backend_is_default(self, sessions: sessionmaker) -> None:
        from infrastructure.duckdb_store import DuckDbSnapshotStore

        cfg = Settings.from_env()
        object.__setattr__(cfg, "snapshot_backend", "duckdb")
        assert isinstance(build_snapshot_store(cfg, sessions), DuckDbSnapshotStore)
