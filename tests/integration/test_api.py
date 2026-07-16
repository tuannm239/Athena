"""Integration tests — REST API (Sprint 3, SPEC-08).

Runs the full app over SQLite in-memory with real JWT auth, exercising
the envelope, error mapping, auth flow, and decision/portfolio resources.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

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
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    app = create_app(settings=_settings(), session_factory=factory)
    return TestClient(app)


def _register_and_login(client: TestClient) -> dict[str, str]:
    r = client.post(
        "/api/v1/auth/register",
        json={"email": "investor@example.com", "password": "s3cret-pass"},
    )
    assert r.status_code == 201, r.text
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "investor@example.com", "password": "s3cret-pass"},
    )
    assert r.status_code == 200, r.text
    tokens: dict[str, str] = r.json()["data"]
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _decision_payload() -> dict[str, Any]:
    return {
        "hypothesis": "Company X outperforms its sector over 12 months",
        "probability": "0.62",
        "confidence": "0.71",
        "decision_type": "WATCHLIST",
        "assumptions": ["margins hold"],
        "invalidation_conditions": ["guidance cut"],
        "evidence": [
            {
                "source": "10-K",
                "category": "fundamental",
                "explanation": "strong FCF",
                "reliability": "0.8",
                "direction": "SUPPORTING",
            },
            {
                "source": "street",
                "category": "valuation",
                "explanation": "rich multiple",
                "reliability": "0.6",
                "direction": "CONTRADICTING",
            },
        ],
    }


class TestOps:
    def test_health_and_docs(self, client: TestClient) -> None:
        assert client.get("/health").status_code == 200
        assert client.get("/docs").status_code == 200
        assert client.get("/openapi.json").json()["info"]["title"] == "ATHENA"


class TestEnvelope:
    def test_ok_envelope_shape_and_request_id_echo(self, client: TestClient) -> None:
        r = client.post(
            "/api/v1/auth/register",
            json={"email": "a@b.co", "password": "longenough"},
            headers={"X-Request-ID": "req-123"},
        )
        body = r.json()
        assert body["request_id"] == "req-123"
        assert body["status"] == "ok"
        assert r.headers["X-Request-ID"] == "req-123"

    def test_error_envelope_shape(self, client: TestClient) -> None:
        r = client.get("/api/v1/decisions")
        assert r.status_code == 401
        body = r.json()
        assert body["status"] == "error"
        assert body["errors"][0]["code"] == "Unauthorized"


class TestAuth:
    def test_register_login_refresh_flow(self, client: TestClient) -> None:
        headers = _register_and_login(client)
        assert client.get("/api/v1/decisions", headers=headers).status_code == 200

        login = client.post(
            "/api/v1/auth/login",
            json={"email": "investor@example.com", "password": "s3cret-pass"},
        ).json()["data"]
        refreshed = client.post(
            "/api/v1/auth/refresh", json={"refresh_token": login["refresh_token"]}
        )
        assert refreshed.status_code == 200
        new_access = refreshed.json()["data"]["access_token"]
        ok = client.get("/api/v1/decisions", headers={"Authorization": f"Bearer {new_access}"})
        assert ok.status_code == 200

    def test_duplicate_email_conflicts(self, client: TestClient) -> None:
        _register_and_login(client)
        r = client.post(
            "/api/v1/auth/register",
            json={"email": "investor@example.com", "password": "s3cret-pass"},
        )
        assert r.status_code == 409
        assert r.json()["errors"][0]["code"] == "Conflict"

    def test_wrong_password_is_401(self, client: TestClient) -> None:
        _register_and_login(client)
        r = client.post(
            "/api/v1/auth/login",
            json={"email": "investor@example.com", "password": "wrong-password"},
        )
        assert r.status_code == 401

    def test_access_token_rejected_for_refresh(self, client: TestClient) -> None:
        _register_and_login(client)
        login = client.post(
            "/api/v1/auth/login",
            json={"email": "investor@example.com", "password": "s3cret-pass"},
        ).json()["data"]
        r = client.post("/api/v1/auth/refresh", json={"refresh_token": login["access_token"]})
        assert r.status_code == 401


class TestDecisionsResource:
    def test_create_get_list_roundtrip(self, client: TestClient) -> None:
        headers = _register_and_login(client)
        created = client.post("/api/v1/decisions", json=_decision_payload(), headers=headers)
        assert created.status_code == 201, created.text
        decision = created.json()["data"]
        assert decision["status"] == "DRAFT"
        assert decision["probability"] == "0.62"

        got = client.get(f"/api/v1/decisions/{decision['id']}", headers=headers)
        assert got.status_code == 200
        assert got.json()["data"]["evidence"][0]["explanation"] == "strong FCF"

        page = client.get("/api/v1/decisions?limit=10&offset=0", headers=headers).json()["data"]
        assert page["total"] == 1 and len(page["items"]) == 1

    def test_lifecycle_via_patch(self, client: TestClient) -> None:
        headers = _register_and_login(client)
        decision = client.post(
            "/api/v1/decisions", json=_decision_payload(), headers=headers
        ).json()["data"]
        did = decision["id"]

        risk = {
            "var": "0.05",
            "cvar": "0.08",
            "max_drawdown": "0.25",
            "stress_score": "0.4",
            "liquidity_score": "0.7",
            "level": "MODERATE",
            "confidence": "0.9",
        }
        r = client.patch(
            f"/api/v1/decisions/{did}",
            json={"risk_assessment": risk, "status": "UNDER_REVIEW"},
            headers=headers,
        )
        assert r.status_code == 200, r.text
        r = client.patch(
            f"/api/v1/decisions/{did}",
            json={"status": "APPROVED", "review_note": "ok"},
            headers=headers,
        )
        assert r.status_code == 200
        body = r.json()["data"]
        assert body["status"] == "APPROVED"
        assert [h["outcome"] for h in body["review_history"]] == ["UNDER_REVIEW", "APPROVED"]

    def test_invalid_transition_is_409(self, client: TestClient) -> None:
        headers = _register_and_login(client)
        decision = client.post(
            "/api/v1/decisions", json=_decision_payload(), headers=headers
        ).json()["data"]
        r = client.patch(
            f"/api/v1/decisions/{decision['id']}", json={"status": "ARCHIVED"}, headers=headers
        )
        assert r.status_code == 409
        assert r.json()["errors"][0]["code"] == "Conflict"

    def test_approval_without_risk_is_422(self, client: TestClient) -> None:
        headers = _register_and_login(client)
        decision = client.post(
            "/api/v1/decisions", json=_decision_payload(), headers=headers
        ).json()["data"]
        client.patch(
            f"/api/v1/decisions/{decision['id']}",
            json={"status": "UNDER_REVIEW"},
            headers=headers,
        )
        r = client.patch(
            f"/api/v1/decisions/{decision['id']}", json={"status": "APPROVED"}, headers=headers
        )
        assert r.status_code == 422
        assert r.json()["errors"][0]["code"] == "BusinessRuleViolation"

    def test_request_validation_is_400(self, client: TestClient) -> None:
        headers = _register_and_login(client)
        r = client.post(
            "/api/v1/decisions",
            json={"hypothesis": "", "probability": "0.5", "confidence": "0.5"},
            headers=headers,
        )
        assert r.status_code == 400
        assert r.json()["errors"][0]["code"] == "ValidationError"

    def test_missing_decision_is_404(self, client: TestClient) -> None:
        headers = _register_and_login(client)
        r = client.get("/api/v1/decisions/00000000-0000-0000-0000-000000000000", headers=headers)
        assert r.status_code == 404


class TestPortfoliosResource:
    def test_create_get_list_positions(self, client: TestClient) -> None:
        headers = _register_and_login(client)
        created = client.post(
            "/api/v1/portfolios",
            json={"base_currency": "VND", "cash": "1000000"},
            headers=headers,
        )
        assert created.status_code == 201, created.text
        pid = created.json()["data"]["id"]

        got = client.get(f"/api/v1/portfolios/{pid}", headers=headers)
        assert got.status_code == 200
        assert Decimal(got.json()["data"]["cash"]) == Decimal("1000000")

        page = client.get("/api/v1/portfolios", headers=headers).json()["data"]
        assert page["total"] == 1

        positions = client.get(f"/api/v1/portfolios/{pid}/positions", headers=headers)
        assert positions.status_code == 200
        assert positions.json()["data"] == []

    def test_other_users_portfolio_is_404(self, client: TestClient) -> None:
        headers = _register_and_login(client)
        pid = client.post(
            "/api/v1/portfolios",
            json={"base_currency": "VND", "cash": "1"},
            headers=headers,
        ).json()["data"]["id"]

        client.post(
            "/api/v1/auth/register", json={"email": "other@example.com", "password": "s3cret-pass"}
        )
        other_tokens = client.post(
            "/api/v1/auth/login", json={"email": "other@example.com", "password": "s3cret-pass"}
        ).json()["data"]
        r = client.get(
            f"/api/v1/portfolios/{pid}",
            headers={"Authorization": f"Bearer {other_tokens['access_token']}"},
        )
        assert r.status_code == 404


class TestSpecPathsPending:
    def test_spec08_pending_groups_return_501(self, client: TestClient) -> None:
        headers = _register_and_login(client)
        for method, path in (
            ("GET", "/api/v1/market/context"),
            ("GET", "/api/v1/market/regime"),
            ("GET", "/api/v1/market/sectors"),
            ("GET", "/api/v1/companies/ABC/factors"),
            ("GET", "/api/v1/companies/ABC/research"),
            ("POST", "/api/v1/backtests"),
            ("GET", "/api/v1/backtests/00000000-0000-0000-0000-000000000000"),
        ):
            response = client.request(method, path, headers=headers)
            assert response.status_code == 501, (method, path, response.status_code)

    def test_unknown_company_profile_is_404(self, client: TestClient) -> None:
        headers = _register_and_login(client)
        r = client.get("/api/v1/companies/NOPE", headers=headers)
        assert r.status_code == 404
