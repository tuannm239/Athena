"""Integration — investment universe management API (editable watchlist).

Full app over in-memory SQLite: list is empty until seeded/added; an
ANALYST can add, edit (level/active), and remove symbols; reads require auth.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.main import create_app
from infrastructure.config import Settings
from infrastructure.db.base import Base


def _settings() -> Settings:
    return Settings(
        database_url="sqlite://",
        redis_url="redis://localhost:6379/0",
        duckdb_dir="data/snapshots",
        jwt_secret="test-secret",
        access_token_ttl_seconds=900,
        refresh_token_ttl_seconds=3600,
    )


@pytest.fixture()
def client() -> TestClient:
    engine = create_engine(
        "sqlite+pysqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    app = create_app(
        settings=_settings(), session_factory=sessionmaker(bind=engine, expire_on_commit=False)
    )
    return TestClient(app)


def _auth(client: TestClient) -> dict[str, str]:
    client.post("/api/v1/auth/register", json={"email": "a@e.com", "password": "s3cret-pass"})
    r = client.post("/api/v1/auth/login", json={"email": "a@e.com", "password": "s3cret-pass"})
    return {"Authorization": f"Bearer {r.json()['data']['access_token']}"}


def test_universe_requires_auth(client: TestClient) -> None:
    assert client.get("/api/v1/universe").status_code == 401


def test_crud_lifecycle(client: TestClient) -> None:
    headers = _auth(client)

    # empty to start (test DB is not seeded)
    r = client.get("/api/v1/universe", headers=headers)
    assert r.status_code == 200 and r.json()["data"] == []

    # add
    r = client.post(
        "/api/v1/universe",
        headers=headers,
        json={"symbol": "fpt", "sector": "TECHNOLOGY", "sync_level": "REALTIME"},
    )
    assert r.status_code == 200, r.text
    entry = r.json()["data"]
    assert entry["symbol"] == "FPT" and entry["sync_level"] == "REALTIME" and entry["is_active"]

    # list now has it
    r = client.get("/api/v1/universe", headers=headers)
    assert [e["symbol"] for e in r.json()["data"]] == ["FPT"]

    # edit: deactivate + change level
    r = client.patch(
        "/api/v1/universe/FPT", headers=headers, json={"is_active": False, "sync_level": "LOW"}
    )
    assert r.status_code == 200
    assert r.json()["data"]["is_active"] is False and r.json()["data"]["sync_level"] == "LOW"

    # remove
    assert client.delete("/api/v1/universe/FPT", headers=headers).status_code == 200
    r = client.get("/api/v1/universe", headers=headers)
    assert r.json()["data"] == []

    # patch/delete unknown -> 404
    assert client.patch("/api/v1/universe/NOPE", headers=headers, json={}).status_code == 404
    assert client.delete("/api/v1/universe/NOPE", headers=headers).status_code == 404
