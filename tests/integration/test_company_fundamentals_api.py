"""Integration — company fundamentals endpoint (honest-empty vs persisted)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.main import create_app
from infrastructure.config import Settings
from infrastructure.db.base import Base
from infrastructure.db.repositories.company_fundamentals import SqlCompanyFundamentalsRepository


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
def ctx() -> tuple[TestClient, sessionmaker]:
    engine = create_engine(
        "sqlite+pysqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    return TestClient(create_app(settings=_settings(), session_factory=factory)), factory


def _auth(client: TestClient) -> dict[str, str]:
    client.post("/api/v1/auth/register", json={"email": "a@e.com", "password": "s3cret-pass"})
    r = client.post("/api/v1/auth/login", json={"email": "a@e.com", "password": "s3cret-pass"})
    return {"Authorization": f"Bearer {r.json()['data']['access_token']}"}


def test_fundamentals_honest_empty_before_sync(ctx: tuple[TestClient, sessionmaker]) -> None:
    client, _ = ctx
    headers = _auth(client)
    r = client.get("/api/v1/companies/FPT/fundamentals", headers=headers)
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert data["ticker"] == "FPT"
    assert data["ratios"]["roe"] is None  # honest empty, never fake
    assert data["quality_score"] is None


def test_fundamentals_returns_persisted_payload(ctx: tuple[TestClient, sessionmaker]) -> None:
    client, factory = ctx
    headers = _auth(client)
    SqlCompanyFundamentalsRepository(factory).upsert(
        "FPT",
        {
            "ticker": "FPT",
            "exchange": "HOSE",
            "sector": "TECHNOLOGY",
            "ratios": {"roe": 0.21, "pe": 9.5},
            "quality_score": 82.0,
            "valuation_score": 60.0,
            "growth_score": 74.0,
            "revenue_growth_yoy": 0.2,
            "eps_growth_yoy": 0.16,
        },
    )
    r = client.get("/api/v1/companies/FPT/fundamentals", headers=headers)
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["ratios"]["roe"] == 0.21 and data["quality_score"] == 82.0
