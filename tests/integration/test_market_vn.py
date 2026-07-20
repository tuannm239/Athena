"""Integration — GET /api/v1/market/vn/snapshot over persisted pipeline data.

Drives the full app (SQLite + real JWT) and asserts the endpoint projects the
Data Pipeline's *published* prices into the snapshot the Market page and
dashboard widgets consume — and returns an honest empty state (never sample)
when nothing has been synchronised. The pipeline is populated the same way a
production sync would: through `ProviderSyncService`, using the same catalog +
snapshot store the app reads from.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from api.main import create_app
from data_pipeline.application.sync import ProviderSyncService
from data_pipeline.application.use_cases import DataPipelineUseCases
from infrastructure.config import Settings
from infrastructure.db.base import Base
from infrastructure.db.repositories.dataset_catalog import SqlDatasetCatalog
from infrastructure.duckdb_store import DuckDbSnapshotStore
from providers.connectors.static import StaticProvider
from providers.sdk.models import PriceBar

AS_OF = datetime(2026, 1, 6, 9, 0, tzinfo=timezone.utc)


def _settings(duckdb_dir: str) -> Settings:
    return Settings(
        database_url="sqlite://",
        redis_url="redis://localhost:6379/0",
        duckdb_dir=duckdb_dir,
        jwt_secret="test-secret-key-at-least-32-chars-long",
        access_token_ttl_seconds=900,
        refresh_token_ttl_seconds=3600,
    )


def _bar(ticker: str, day: date, close: str, volume: str) -> PriceBar:
    return PriceBar(ticker=ticker, day=day, close=Decimal(close), volume=Decimal(volume))


def _seed_provider() -> StaticProvider:
    d1, d2 = date(2026, 1, 5), date(2026, 1, 6)
    return StaticProvider(
        bars=(
            # indices
            _bar("VNINDEX", d1, "1280.00", "0"),
            _bar("VNINDEX", d2, "1293.11", "0"),
            _bar("VN30", d1, "1320.00", "0"),
            _bar("VN30", d2, "1327.00", "0"),
            # stocks: FPT up, HPG down, STB flat
            _bar("FPT", d1, "136.00", "4000000"),
            _bar("FPT", d2, "140.60", "5000000"),
            _bar("HPG", d1, "28.00", "8000000"),
            _bar("HPG", d2, "27.00", "9000000"),
            _bar("STB", d1, "33.00", "6000000"),
            _bar("STB", d2, "33.00", "6500000"),
        )
    )


@pytest.fixture()
def harness(tmp_path: Path) -> tuple[TestClient, Settings, sessionmaker[Session]]:
    engine = create_engine(
        "sqlite+pysqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    settings = _settings(str(tmp_path / "snapshots"))
    app = create_app(settings=settings, session_factory=factory)
    return TestClient(app), settings, factory


def _auth(client: TestClient) -> dict[str, str]:
    client.post(
        "/api/v1/auth/register", json={"email": "vn@example.com", "password": "s3cret-pass"}
    )
    r = client.post(
        "/api/v1/auth/login", json={"email": "vn@example.com", "password": "s3cret-pass"}
    )
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['data']['access_token']}"}


def _publish_prices(settings: Settings, factory: sessionmaker[Session]) -> None:
    pipeline = DataPipelineUseCases(
        catalog=SqlDatasetCatalog(factory), snapshots=DuckDbSnapshotStore(settings.duckdb_dir)
    )
    sync = ProviderSyncService(pipeline=pipeline, source="provider:test")
    sync.full_sync_prices(
        _seed_provider(),
        ["VNINDEX", "VN30", "FPT", "HPG", "STB"],
        date(2026, 1, 5),
        date(2026, 1, 6),
        as_of=AS_OF,
    )


class TestSnapshotWithData:
    def test_snapshot_projects_persisted_prices(
        self, harness: tuple[TestClient, Settings, sessionmaker[Session]]
    ) -> None:
        client, settings, factory = harness
        _publish_prices(settings, factory)
        headers = _auth(client)

        r = client.get("/api/v1/market/vn/snapshot", headers=headers)
        assert r.status_code == 200, r.text
        snap = r.json()["data"]

        # Indices (VNINDEX, VN30) come from the persisted price rows.
        by_code = {i["code"]: i for i in snap["indices"]}
        assert set(by_code) == {"VNINDEX", "VN30"}
        vnindex = by_code["VNINDEX"]
        assert vnindex["value"] == pytest.approx(1293.11)
        assert vnindex["change"] == pytest.approx(13.11)
        assert vnindex["change_pct"] == pytest.approx((1293.11 - 1280.0) / 1280.0)

        # Movers exclude indices; FPT up, HPG down.
        assert snap["top_gainers"][0]["ticker"] == "FPT"
        assert snap["top_losers"][0]["ticker"] == "HPG"
        assert {m["ticker"] for m in snap["top_volume"]} <= {"FPT", "HPG", "STB"}

        # Breadth over the 3 stocks: 1 up, 1 down, 1 flat.
        assert snap["breadth"] == {"advancers": 1, "decliners": 1, "unchanged": 1}

        # Liquidity = sum(close × volume) over stocks (latest day) > 0.
        assert snap["liquidity_value"] > 0

    def test_fields_without_persisted_source_are_empty(
        self, harness: tuple[TestClient, Settings, sessionmaker[Session]]
    ) -> None:
        client, settings, factory = harness
        _publish_prices(settings, factory)
        r = client.get("/api/v1/market/vn/snapshot", headers=_auth(client))
        snap = r.json()["data"]
        # No persisted source yet → honest empties, not sample values.
        assert snap["sector_heatmap"] == []
        assert snap["foreign"] == {"buy_value": 0.0, "sell_value": 0.0, "net_value": 0.0}
        assert snap["proprietary"] == {"buy_value": 0.0, "sell_value": 0.0, "net_value": 0.0}
        assert snap["new_high"] == 0 and snap["new_low"] == 0


class TestSnapshotEmptyState:
    def test_no_data_returns_empty_not_sample(
        self, harness: tuple[TestClient, Settings, sessionmaker[Session]]
    ) -> None:
        client, _settings, _factory = harness  # nothing published
        r = client.get("/api/v1/market/vn/snapshot", headers=_auth(client))
        assert r.status_code == 200, r.text
        snap = r.json()["data"]
        assert snap["indices"] == []
        assert snap["top_gainers"] == [] and snap["top_losers"] == []
        assert snap["breadth"] == {"advancers": 0, "decliners": 0, "unchanged": 0}
        assert snap["liquidity_value"] == 0.0
        assert snap["as_of"] is None


class TestSnapshotAuth:
    def test_requires_authentication(
        self, harness: tuple[TestClient, Settings, sessionmaker[Session]]
    ) -> None:
        client, _s, _f = harness
        r = client.get("/api/v1/market/vn/snapshot")
        assert r.status_code in (401, 403)
