"""Unit tests — infrastructure adapters (Sprint 2, SPEC-07)."""

from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

from infrastructure.cache import RedisCache
from infrastructure.config import Settings
from infrastructure.duckdb_store import DuckDbSnapshotStore, SnapshotImmutabilityError


class TestSettings:
    def test_defaults_match_compose(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.delenv("REDIS_URL", raising=False)
        settings = Settings.from_env()
        assert settings.database_url.startswith("postgresql+psycopg://athena:")
        assert settings.redis_url.startswith("redis://")

    def test_env_overrides(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DATABASE_URL", "sqlite:///x.db")
        assert Settings.from_env().database_url == "sqlite:///x.db"


class TestDuckDbSnapshotStore:
    def _frame(self) -> pl.DataFrame:
        return pl.DataFrame({"ticker": ["AAA", "BBB"], "close": [10.5, 20.25]})

    def test_write_read_round_trip(self, tmp_path: Path) -> None:
        store = DuckDbSnapshotStore(tmp_path)
        store.write("snap-001", "prices", self._frame())
        loaded = store.read("snap-001", "prices")
        assert loaded.equals(self._frame())
        assert store.tables("snap-001") == ("prices",)

    def test_snapshots_are_immutable(self, tmp_path: Path) -> None:
        store = DuckDbSnapshotStore(tmp_path)
        store.write("snap-001", "prices", self._frame())
        with pytest.raises(SnapshotImmutabilityError):
            store.write("snap-001", "prices", self._frame())

    def test_repeated_reads_are_identical(self, tmp_path: Path) -> None:
        store = DuckDbSnapshotStore(tmp_path)
        store.write("snap-002", "prices", self._frame())
        assert store.read("snap-002", "prices").equals(store.read("snap-002", "prices"))

    def test_invalid_snapshot_id_rejected(self, tmp_path: Path) -> None:
        store = DuckDbSnapshotStore(tmp_path)
        with pytest.raises(ValueError):
            store.write("../escape", "prices", self._frame())

    def test_missing_snapshot_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            DuckDbSnapshotStore(tmp_path).read("nope", "prices")


def _redis_available() -> bool:
    return RedisCache(Settings.from_env().redis_url).ping()


@pytest.mark.skipif(not _redis_available(), reason="Redis not reachable (runs in CI)")
class TestRedisCache:
    def test_set_get_delete_and_ttl_validation(self) -> None:
        cache = RedisCache(Settings.from_env().redis_url)
        cache.set("athena:test:key", "value", ttl_seconds=30)
        assert cache.get("athena:test:key") == "value"
        cache.delete("athena:test:key")
        assert cache.get("athena:test:key") is None
        with pytest.raises(ValueError):
            cache.set("k", "v", ttl_seconds=0)

    def test_idempotency_key_single_owner(self) -> None:
        cache = RedisCache(Settings.from_env().redis_url)
        cache.delete("athena:test:idem")
        assert cache.acquire_idempotency_key("athena:test:idem", ttl_seconds=30) is True
        assert cache.acquire_idempotency_key("athena:test:idem", ttl_seconds=30) is False
        cache.delete("athena:test:idem")
