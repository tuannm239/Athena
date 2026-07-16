"""Integration tests — persistence layer (Sprint 2, SPEC-07).

Repository round-trips run against SQLite in-memory (the models use
portable types); the same suite runs against PostgreSQL in CI via
DATABASE_URL. Redis tests are skipped when no server is reachable.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from decision_kernel.domain.decision import Decision, DecisionStatus, DecisionType
from decision_kernel.domain.evidence import Evidence, EvidenceDirection
from identity.domain.user import User
from infrastructure.db.base import Base
from infrastructure.db.models import AuditRow
from infrastructure.db.repositories.decision import SqlDecisionRepository
from infrastructure.db.repositories.portfolio import SqlPortfolioRepository
from infrastructure.db.repositories.user import SqlUserRepository
from portfolio.domain.constraints import PortfolioConstraints
from portfolio.domain.portfolio import Portfolio
from portfolio.domain.position import Position
from risk.domain.risk_assessment import RiskAssessment, RiskLevel
from shared_kernel.measures import Percentage
from shared_kernel.money import Currency, Money
from shared_kernel.probability import Confidence, Probability, Reliability


@pytest.fixture()
def sessions() -> sessionmaker[Session]:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def _user() -> User:
    return User(email="investor@example.com", status="active")


def _decision() -> Decision:
    d = Decision(
        hypothesis="Company X outperforms its sector over 12 months",
        probability=Probability(Decimal("0.62")),
        confidence=Confidence(Decimal("0.71")),
        decision_type=DecisionType.WATCHLIST,
        expected_return=Decimal("0.15"),
        expected_drawdown=Decimal("0.2"),
        assumptions=("margins hold",),
    )
    d.add_evidence(
        Evidence(
            source="10-K",
            category="fundamental",
            explanation="strong FCF",
            reliability=Reliability(Decimal("0.8")),
            direction=EvidenceDirection.SUPPORTING,
            metadata={"filing": "2025-10K"},
        )
    )
    d.add_evidence(
        Evidence(
            source="street",
            category="valuation",
            explanation="rich multiple",
            reliability=Reliability(Decimal("0.6")),
            direction=EvidenceDirection.CONTRADICTING,
        )
    )
    d.attach_risk_assessment(
        RiskAssessment(
            var=Decimal("0.05"),
            cvar=Decimal("0.08"),
            max_drawdown=Decimal("0.25"),
            stress_score=Decimal("0.4"),
            liquidity_score=Decimal("0.7"),
            level=RiskLevel.MODERATE,
            confidence=Confidence(Decimal("0.9")),
        )
    )
    d.invalidation_conditions = ("guidance cut",)
    return d


class TestUserRepository:
    def test_round_trip_and_lookup_by_email(self, sessions: sessionmaker[Session]) -> None:
        repo = SqlUserRepository(sessions)
        user = _user()
        repo.save(user)
        loaded = repo.get(user.id)
        assert loaded is not None and loaded.email == user.email
        by_email = repo.get_by_email(user.email)
        assert by_email is not None and by_email.id == user.id
        assert repo.get_by_email("missing@example.com") is None


class TestDecisionRepository:
    def test_full_aggregate_round_trip(self, sessions: sessionmaker[Session]) -> None:
        repo = SqlDecisionRepository(sessions)
        decision = _decision()
        decision.submit_for_review()
        decision.approve(note="ok")
        repo.save(decision)

        loaded = repo.get(decision.id)
        assert loaded is not None
        assert loaded.status is DecisionStatus.APPROVED
        assert loaded.hypothesis == decision.hypothesis
        assert loaded.probability.value == Decimal("0.62")
        assert [e.explanation for e in loaded.supporting_evidence] == ["strong FCF"]
        assert [e.explanation for e in loaded.contradicting_evidence] == ["rich multiple"]
        assert loaded.supporting_evidence[0].metadata["filing"] == "2025-10K"
        assert loaded.risk_assessment is not None
        assert loaded.risk_assessment.level is RiskLevel.MODERATE
        assert loaded.risk_assessment.var == Decimal("0.05")
        assert [r.outcome for r in loaded.review_history] == [
            DecisionStatus.UNDER_REVIEW,
            DecisionStatus.APPROVED,
        ]
        assert loaded.pull_events() == ()

    def test_missing_returns_none(self, sessions: sessionmaker[Session]) -> None:
        assert SqlDecisionRepository(sessions).get(_decision().id) is None

    def test_updates_write_audit_records(self, sessions: sessionmaker[Session]) -> None:
        repo = SqlDecisionRepository(sessions)
        decision = _decision()
        repo.save(decision)
        decision.submit_for_review()
        repo.save(decision)

        with sessions() as session:
            rows = session.scalars(select(AuditRow).order_by(AuditRow.created_at)).all()
        decision_audits = [r for r in rows if r.entity_type == "decision"]
        assert [r.action for r in decision_audits] == ["CREATE", "UPDATE"]
        assert all(r.entity_id == decision.id.value for r in decision_audits)


class TestPortfolioRepository:
    def _portfolio(self, owner: User) -> Portfolio:
        return Portfolio(
            owner_id=owner.id,
            cash_balance=Money(Decimal("1000"), Currency.VND),
            positions=(
                Position(
                    ticker="AAA",
                    quantity=Decimal("100"),
                    average_cost=Money(Decimal("10"), Currency.VND),
                    market_value=Money(Decimal("500"), Currency.VND),
                    unrealized_pnl=Money(Decimal("-500"), Currency.VND),
                ),
            ),
            constraints=PortfolioConstraints(max_position_weight=Percentage(Decimal("0.2"))),
        )

    def test_round_trip_with_positions_and_constraints(
        self, sessions: sessionmaker[Session]
    ) -> None:
        owner = _user()
        SqlUserRepository(sessions).save(owner)
        repo = SqlPortfolioRepository(sessions)
        portfolio = self._portfolio(owner)
        repo.save(portfolio)

        loaded = repo.get(portfolio.id)
        assert loaded is not None
        assert loaded.owner_id == owner.id
        assert loaded.cash_balance == Money(Decimal("1000"), Currency.VND)
        assert len(loaded.positions) == 1
        assert loaded.positions[0].ticker == "AAA"
        assert loaded.positions[0].market_value.amount == Decimal("500")
        assert loaded.constraints.max_position_weight == Percentage(Decimal("0.2"))

    def test_update_replaces_positions_and_audits(self, sessions: sessionmaker[Session]) -> None:
        owner = _user()
        SqlUserRepository(sessions).save(owner)
        repo = SqlPortfolioRepository(sessions)
        portfolio = self._portfolio(owner)
        repo.save(portfolio)
        portfolio.remove_position("AAA")
        repo.save(portfolio)

        loaded = repo.get(portfolio.id)
        assert loaded is not None and loaded.positions == ()
        with sessions() as session:
            actions = [
                r.action
                for r in session.scalars(
                    select(AuditRow).where(AuditRow.entity_type == "portfolio")
                ).all()
            ]
        assert actions == ["CREATE", "UPDATE"]


class TestTimestamps:
    def test_created_at_survives_round_trip_as_utc(self, sessions: sessionmaker[Session]) -> None:
        repo = SqlDecisionRepository(sessions)
        decision = _decision()
        repo.save(decision)
        loaded = repo.get(decision.id)
        assert loaded is not None
        got = loaded.created_at.replace(tzinfo=timezone.utc)
        assert abs((got - decision.created_at).total_seconds()) < 1
        assert isinstance(loaded.created_at, datetime)


class TestProbabilityOverStoredDecision:
    def test_evaluate_decision_report(self, sessions: sessionmaker[Session]) -> None:
        from probability.application.use_cases import ProbabilityUseCases

        repo = SqlDecisionRepository(sessions)
        decision = _decision()
        repo.save(decision)
        report = ProbabilityUseCases(decisions=repo).evaluate_decision(
            decision.id, as_of=datetime.now(timezone.utc)
        )
        assert report.hypothesis == decision.hypothesis
        assert report.prior.value == Decimal("0.62")
        assert len(report.evidence_summary) == 2


class TestJournalRepository:
    def test_append_and_read_immutable_entries(self, sessions: sessionmaker[Session]) -> None:
        from behavior.domain.journal import DecisionJournalEntry
        from behavior.domain.repository import JournalRepository
        from infrastructure.db.repositories.journal import SqlJournalRepository
        from shared_kernel.identifiers import DecisionId

        repo: JournalRepository = SqlJournalRepository(sessions)
        decision_id = DecisionId()
        entry = DecisionJournalEntry(
            decision_id=decision_id,
            original_hypothesis="X outperforms",
            supporting_evidence=("strong FCF",),
            counter_evidence=("rich multiple",),
            expected_outcome="+15% in 12m",
            actual_outcome="+9% in 12m",
            lessons_learned="size smaller in consolidation regimes",
        )
        repo.append(entry)
        loaded = repo.for_decision(decision_id)
        assert len(loaded) == 1
        assert loaded[0].lessons_learned.startswith("size smaller")
        assert repo.all_entries()
