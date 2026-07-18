"""Phase 5 W6 — Pilot Mode: config flag, /pilot/status posture, daily report.

Pilot Mode is an *operational* assertion (read-only markets, no order
execution, no broker, human approval mandatory). Athena has no execution
path by construction, so these tests verify the surfaced posture and the
retained daily record — not any new business logic.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

import pytest
from fastapi.testclient import TestClient
from scripts.daily_report import generate_report, render_markdown
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from api.main import create_app
from infrastructure.config import Settings
from infrastructure.db.base import Base
from infrastructure.db.models import AuditRow, DecisionRow


def _settings(pilot: bool = False) -> Settings:
    return Settings(
        database_url="sqlite://",
        redis_url="redis://localhost:1/0",
        duckdb_dir="data/snapshots",
        jwt_secret="test-secret",
        access_token_ttl_seconds=900,
        refresh_token_ttl_seconds=3600,
        pilot_mode=pilot,
    )


class TestConfigFlag:
    def test_defaults_off(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("ATHENA_PILOT_MODE", raising=False)
        assert Settings.from_env().pilot_mode is False

    @pytest.mark.parametrize("value", ["1", "true", "TRUE", "yes", "Yes"])
    def test_truthy_values_enable(self, value: str, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ATHENA_PILOT_MODE", value)
        assert Settings.from_env().pilot_mode is True

    @pytest.mark.parametrize("value", ["0", "false", "no", "off", ""])
    def test_falsy_values_disable(self, value: str, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ATHENA_PILOT_MODE", value)
        assert Settings.from_env().pilot_mode is False


@pytest.fixture()
def factory() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite+pysqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


class TestPilotStatusEndpoint:
    def test_reports_decision_support_posture(self, factory: sessionmaker[Session]) -> None:
        client = TestClient(create_app(settings=_settings(pilot=True), session_factory=factory))
        payload = client.get("/pilot/status").json()
        # The non-negotiable guarantees must be asserted false/true explicitly.
        assert payload["pilot_mode"] is True
        assert payload["order_execution"] is False
        assert payload["broker_integration"] is False
        assert payload["read_only_market_access"] is True
        assert payload["human_approval_required"] is True
        assert payload["audit_trail"] is True

    def test_health_full_surfaces_pilot_mode(self, factory: sessionmaker[Session]) -> None:
        client = TestClient(create_app(settings=_settings(pilot=True), session_factory=factory))
        assert client.get("/health/full").json()["pilot_mode"] is True

    def test_pilot_mode_off_by_default(self, factory: sessionmaker[Session]) -> None:
        client = TestClient(create_app(settings=_settings(pilot=False), session_factory=factory))
        assert client.get("/pilot/status").json()["pilot_mode"] is False
        # even with pilot flag off, the structural guarantees hold
        assert client.get("/pilot/status").json()["order_execution"] is False


def _decision(status: str, created_at: datetime) -> DecisionRow:
    return DecisionRow(
        id=uuid.uuid4(),
        hypothesis="h",
        probability=0,
        confidence=0,
        status=status,
        assumptions=[],
        invalidation_conditions=[],
        review_history=[],
        created_at=created_at,
    )


def _audit(action: str, status: str, created_at: datetime) -> AuditRow:
    return AuditRow(
        entity_type="decision",
        entity_id=uuid.uuid4(),
        action=action,
        snapshot={"status": status, "hypothesis": "h"},
        created_at=created_at,
    )


class TestDailyReport:
    def test_counts_decisions_reviews_and_audit_for_the_day(
        self, factory: sessionmaker[Session]
    ) -> None:
        day = date(2026, 7, 17)
        in_day = datetime(2026, 7, 17, 10, tzinfo=timezone.utc)
        other_day = datetime(2026, 7, 16, 10, tzinfo=timezone.utc)
        with factory() as session:
            session.add_all(
                [
                    _decision("DRAFT", in_day),
                    _decision("UNDER_REVIEW", in_day),
                    _decision("APPROVED", other_day),  # different day, excluded from "today"
                    _audit("CREATE", "DRAFT", in_day),
                    _audit("UPDATE", "APPROVED", in_day),  # a human approval today
                    _audit("UPDATE", "REJECTED", in_day),  # a human rejection today
                    _audit("UPDATE", "APPROVED", other_day),  # different day, excluded
                ]
            )
            session.commit()

        report = generate_report(factory, day)

        assert report["pilot_mode"] is True
        assert report["order_execution"] is False
        assert report["decisions_created_today"] == 2
        assert report["decisions_created_by_status"] == {"DRAFT": 1, "UNDER_REVIEW": 1}
        assert report["reviews_today"] == {"approved": 1, "rejected": 1}
        # lifetime spans all days
        assert report["lifetime_decisions_by_status"]["APPROVED"] == 1
        assert report["audit_events_today"]["decision:UPDATE"] == 2
        assert report["audit_events_today"]["decision:CREATE"] == 1

    def test_empty_day_renders_clean_markdown(self, factory: sessionmaker[Session]) -> None:
        report = generate_report(factory, date(2026, 7, 17))
        assert report["decisions_created_today"] == 0
        markdown = render_markdown(report)
        assert "Pilot Daily Report" in markdown
        assert "Order execution: **DISABLED**" in markdown
        assert "(none)" in markdown
