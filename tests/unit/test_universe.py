"""Investment universe — seed data + SQL repository (editable, no hardcoding).

Verifies the default universe composition and tiers, and the SQL repository's
seed/idempotency/level-filter/edit behaviour on an in-memory SQLite DB.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from data_pipeline.universe import (
    DEFAULT_UNIVERSE,
    SyncLevel,
    UniverseEntry,
)
from infrastructure.db.base import Base
from infrastructure.db.repositories.universe import SqlUniverseRepository


class TestDefaultUniverse:
    def test_covers_expected_symbols_and_is_deduped(self) -> None:
        symbols = [e.symbol for e in DEFAULT_UNIVERSE]
        assert len(symbols) == len(set(symbols))  # no duplicates
        # spot-check one per a few sectors
        by_symbol = {e.symbol: e for e in DEFAULT_UNIVERSE}
        assert by_symbol["VCB"].sector == "BANKING"
        assert by_symbol["FPT"].sector == "TECHNOLOGY"
        assert by_symbol["HVN"].sector == "AVIATION"

    def test_sync_level_tiers(self) -> None:
        by_symbol = {e.symbol: e for e in DEFAULT_UNIVERSE}
        for s in ("FPT", "VCB", "HPG", "SSI", "TCB"):
            assert by_symbol[s].sync_level is SyncLevel.REALTIME
        for s in ("MWG", "VNM", "MBB", "ACB", "VHM"):
            assert by_symbol[s].sync_level is SyncLevel.HIGH
        assert by_symbol["STB"].sync_level is SyncLevel.NORMAL

    def test_priority_derived_from_level(self) -> None:
        assert UniverseEntry("X", "S", SyncLevel.REALTIME).priority == 1
        assert UniverseEntry("X", "S", SyncLevel.LOW).priority == 4


@pytest.fixture()
def repo() -> SqlUniverseRepository:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    return SqlUniverseRepository(sessionmaker(bind=engine, expire_on_commit=False))


class TestRepository:
    def test_seed_then_active_symbols(self, repo: SqlUniverseRepository) -> None:
        added = repo.seed_if_empty(DEFAULT_UNIVERSE)
        assert added == len(DEFAULT_UNIVERSE)
        assert set(repo.active_symbols()) == {e.symbol for e in DEFAULT_UNIVERSE}

    def test_seed_is_idempotent(self, repo: SqlUniverseRepository) -> None:
        repo.seed_if_empty(DEFAULT_UNIVERSE)
        assert repo.seed_if_empty(DEFAULT_UNIVERSE) == 0  # already populated

    def test_level_filter(self, repo: SqlUniverseRepository) -> None:
        repo.seed_if_empty(DEFAULT_UNIVERSE)
        assert set(repo.active_symbols(SyncLevel.REALTIME)) == {"FPT", "VCB", "HPG", "SSI", "TCB"}

    def test_editable_upsert_and_deactivate(self, repo: SqlUniverseRepository) -> None:
        repo.upsert(UniverseEntry("ZZZ", "TEST", SyncLevel.HIGH))
        assert "ZZZ" in repo.active_symbols()
        # editable: change level in place
        repo.upsert(UniverseEntry("ZZZ", "TEST", SyncLevel.LOW))
        assert "ZZZ" in repo.active_symbols(SyncLevel.LOW)
        # deactivate -> excluded from active set
        repo.set_active("ZZZ", False)
        assert "ZZZ" not in repo.active_symbols()

    def test_active_symbols_ordered_by_priority(self, repo: SqlUniverseRepository) -> None:
        repo.seed_if_empty(DEFAULT_UNIVERSE)
        symbols = repo.active_symbols()
        # REALTIME (priority 1) names come before a NORMAL (priority 3) name.
        assert symbols.index("FPT") < symbols.index("STB")
