"""Phase 2 Module 6 — /metrics and /health/full (ADR-0018)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.main import create_app
from infrastructure.config import Settings
from infrastructure.db.base import Base


@pytest.fixture()
def client(tmp_path_factory: pytest.TempPathFactory) -> TestClient:
    engine = create_engine(
        "sqlite+pysqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    settings = Settings(
        database_url="sqlite://",
        redis_url="redis://localhost:1/0",  # unreachable on purpose
        duckdb_dir=str(tmp_path_factory.mktemp("snapshots")),
        jwt_secret="test-secret",
        access_token_ttl_seconds=900,
        refresh_token_ttl_seconds=3600,
    )
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    return TestClient(create_app(settings=settings, session_factory=factory))


class TestMetricsEndpoint:
    def test_exposition_format_with_route_template_labels(self, client: TestClient) -> None:
        assert client.get("/health").status_code == 200
        assert client.get("/api/v1/decisions").status_code in (200, 401)

        response = client.get("/metrics")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/plain")
        body = response.text
        assert "athena_http_requests_total" in body
        assert 'path="/health"' in body
        assert "athena_http_request_duration_seconds_bucket" in body
        assert 'athena_app_info{version="' in body
        # label is the route template, not a raw high-cardinality path
        client.get("/api/v1/companies/AAA")
        client.get("/no/such/route")
        body = client.get("/metrics").text
        assert 'path="/companies/{ticker}"' in body
        assert "companies/AAA" not in body
        assert 'path="unmatched"' in body
        assert 'path="/no/such/route"' not in body

    def test_registries_are_isolated_per_app(self, client: TestClient) -> None:
        client.get("/health")
        # Building a second app must not raise duplicate-metric errors
        # and must start from a clean registry.
        engine = create_engine(
            "sqlite+pysqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        Base.metadata.create_all(engine)
        second = TestClient(
            create_app(
                settings=Settings(
                    database_url="sqlite://",
                    redis_url="redis://localhost:1/0",
                    duckdb_dir="data/snapshots",
                    jwt_secret="test-secret",
                    access_token_ttl_seconds=900,
                    refresh_token_ttl_seconds=3600,
                ),
                session_factory=sessionmaker(bind=engine, expire_on_commit=False),
            )
        )
        assert 'path="/health"' not in second.get("/metrics").text


class TestHealthDashboard:
    def test_reports_components_and_degrades_without_failing(self, client: TestClient) -> None:
        response = client.get("/health/full")
        assert response.status_code == 200
        payload = response.json()
        assert payload["components"]["database"] == "ok"
        assert payload["components"]["snapshots"] == "ok"
        assert payload["components"]["redis"].startswith("unavailable")
        assert payload["status"] == "degraded"

    def test_liveness_stays_bare(self, client: TestClient) -> None:
        assert client.get("/health").json() == {"status": "ok"}
