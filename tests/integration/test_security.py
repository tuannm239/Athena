"""Phase 2 Module 7 — RBAC, API keys, refresh rotation, rate limits (ADR-0019)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from api.main import create_app
from identity.domain.user import Role
from infrastructure.config import InsecureConfigurationError, Settings
from infrastructure.db.base import Base
from infrastructure.db.models import AuditRow


def _settings(**overrides: object) -> Settings:
    base: dict[str, object] = dict(
        database_url="sqlite://",
        redis_url="redis://localhost:1/0",
        duckdb_dir="data/snapshots",
        jwt_secret="test-secret",
        access_token_ttl_seconds=900,
        refresh_token_ttl_seconds=3600,
        rate_limit_per_minute=0,  # disabled unless a test enables it
        auth_rate_limit_per_minute=0,
    )
    base.update(overrides)
    return Settings(**base)  # type: ignore[arg-type]


def _factory() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite+pysqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def _client(**overrides: object) -> TestClient:
    return TestClient(create_app(settings=_settings(**overrides), session_factory=_factory()))


def _register_and_login(client: TestClient, email: str = "a@example.com") -> dict[str, str]:
    client.post("/api/v1/auth/register", json={"email": email, "password": "s3cret-pass"})
    r = client.post("/api/v1/auth/login", json={"email": email, "password": "s3cret-pass"})
    tokens: dict[str, str] = r.json()["data"]
    return tokens


def _decision_payload() -> dict[str, object]:
    return {"hypothesis": "H", "probability": "0.5", "confidence": "0.5"}


class TestRbac:
    def test_viewer_is_read_only(self) -> None:
        client = _client()
        container = client.app.state.container  # type: ignore[attr-defined]
        container.register_user.execute("viewer@example.com", "s3cret-pass", role=Role.VIEWER)
        r = client.post(
            "/api/v1/auth/login",
            json={"email": "viewer@example.com", "password": "s3cret-pass"},
        )
        headers = {"Authorization": f"Bearer {r.json()['data']['access_token']}"}

        assert client.get("/api/v1/decisions", headers=headers).status_code == 200
        denied = client.post("/api/v1/decisions", json=_decision_payload(), headers=headers)
        assert denied.status_code == 403
        assert denied.json()["errors"][0]["code"] == "Forbidden"

    def test_analyst_can_write(self) -> None:
        client = _client()
        tokens = _register_and_login(client)
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        assert (
            client.post("/api/v1/decisions", json=_decision_payload(), headers=headers).status_code
            == 201
        )


class TestApiKeys:
    def test_full_lifecycle_and_x_api_key_auth(self) -> None:
        client = _client()
        tokens = _register_and_login(client)
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}

        created = client.post("/api/v1/auth/api-keys", json={"name": "ci"}, headers=headers).json()[
            "data"
        ]
        assert created["api_key"].startswith("athena_")
        assert created["prefix"] == created["api_key"][: len(created["prefix"])]

        # the raw key authenticates without a bearer token
        via_key = client.post(
            "/api/v1/decisions", json=_decision_payload(), headers={"X-API-Key": created["api_key"]}
        )
        assert via_key.status_code == 201

        listed = client.get("/api/v1/auth/api-keys", headers=headers).json()["data"]
        assert [k["name"] for k in listed] == ["ci"]
        assert "api_key" not in listed[0]  # raw key never re-exposed

        assert (
            client.delete(f"/api/v1/auth/api-keys/{created['id']}", headers=headers).status_code
            == 200
        )
        rejected = client.get("/api/v1/decisions", headers={"X-API-Key": created["api_key"]})
        assert rejected.status_code == 401

    def test_unknown_key_is_401(self) -> None:
        client = _client()
        assert (
            client.get("/api/v1/decisions", headers={"X-API-Key": "athena_nope"}).status_code == 401
        )


class TestRefreshRotation:
    def test_refresh_tokens_are_single_use(self) -> None:
        client = _client()
        tokens = _register_and_login(client)

        first = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
        assert first.status_code == 200

        # reuse of the consumed token is rejected (rotation + reuse detection)
        reused = client.post(
            "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
        )
        assert reused.status_code == 401

        # the rotated token works exactly once
        rotated = first.json()["data"]["refresh_token"]
        assert (
            client.post("/api/v1/auth/refresh", json={"refresh_token": rotated}).status_code == 200
        )


class TestRateLimiting:
    def test_auth_endpoints_hit_429(self) -> None:
        client = _client(auth_rate_limit_per_minute=3)
        statuses = [
            client.post(
                "/api/v1/auth/login", json={"email": "x@example.com", "password": "wrong-pass"}
            ).status_code
            for _ in range(5)
        ]
        assert statuses[:3] == [401, 401, 401]
        assert statuses[3] == 429
        r = client.post(
            "/api/v1/auth/login", json={"email": "x@example.com", "password": "wrong-pass"}
        )
        assert r.headers.get("Retry-After") == "60"
        assert r.json()["errors"][0]["code"] == "RateLimited"

    def test_health_and_metrics_are_exempt(self) -> None:
        client = _client(rate_limit_per_minute=1)
        for _ in range(5):
            assert client.get("/health").status_code == 200
            assert client.get("/metrics").status_code == 200


class TestSecretManagement:
    def test_production_refuses_dev_secret(self) -> None:
        with pytest.raises(InsecureConfigurationError):
            create_app(
                settings=_settings(
                    environment="production", jwt_secret="dev-only-secret-change-me"
                ),
                session_factory=_factory(),
            )
        with pytest.raises(InsecureConfigurationError):
            create_app(
                settings=_settings(environment="production", jwt_secret="short"),
                session_factory=_factory(),
            )

    def test_production_accepts_strong_secret(self) -> None:
        app = create_app(
            settings=_settings(environment="production", jwt_secret="x" * 48),
            session_factory=_factory(),
        )
        assert TestClient(app).get("/health").status_code == 200


class TestSecurityAudit:
    def test_auth_events_land_in_audit_trail(self) -> None:
        factory = _factory()
        client = TestClient(create_app(settings=_settings(), session_factory=factory))
        client.post(
            "/api/v1/auth/register", json={"email": "a@example.com", "password": "s3cret-pass"}
        )
        client.post(
            "/api/v1/auth/login", json={"email": "a@example.com", "password": "s3cret-pass"}
        )
        client.post(
            "/api/v1/auth/login", json={"email": "a@example.com", "password": "wrong-password"}
        )
        with factory() as session:
            actions = set(
                session.scalars(
                    select(AuditRow.action).where(AuditRow.entity_type == "security")
                ).all()
            )
        assert {"user.registered", "auth.login.success", "auth.login.failure"} <= actions
