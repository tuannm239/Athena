"""SQLAlchemy implementation of DecisionRepository (SPEC-03, SPEC-07).

Decimals inside JSON documents are stored as strings to stay exact;
the mapper restores them as Decimal on read.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from decision_kernel.domain.decision import (
    Decision,
    DecisionStatus,
    DecisionType,
    ReviewRecord,
)
from decision_kernel.domain.evidence import Evidence
from decision_kernel.domain.repository import DecisionRepository
from infrastructure.db.engine import session_scope
from infrastructure.db.models import DecisionRow, EvidenceRow
from infrastructure.db.repositories._audit import write_audit
from risk.domain.risk_assessment import RiskAssessment, RiskLevel
from shared_kernel.identifiers import DecisionId, EvidenceId
from shared_kernel.measures import PositionSize
from shared_kernel.probability import Confidence, Probability

_SUPPORTING = "SUPPORTING"
_COUNTER = "COUNTER"


def _risk_to_json(assessment: RiskAssessment | None) -> dict[str, Any] | None:
    if assessment is None:
        return None
    return {
        "var": str(assessment.var),
        "cvar": str(assessment.cvar),
        "max_drawdown": str(assessment.max_drawdown),
        "stress_score": str(assessment.stress_score),
        "liquidity_score": str(assessment.liquidity_score),
        "level": assessment.level.value,
        "confidence": str(assessment.confidence.value),
    }


def _risk_from_json(payload: dict[str, Any] | None) -> RiskAssessment | None:
    if payload is None:
        return None
    return RiskAssessment(
        var=Decimal(payload["var"]),
        cvar=Decimal(payload["cvar"]),
        max_drawdown=Decimal(payload["max_drawdown"]),
        stress_score=Decimal(payload["stress_score"]),
        liquidity_score=Decimal(payload["liquidity_score"]),
        level=RiskLevel(payload["level"]),
        confidence=Confidence(Decimal(payload["confidence"])),
    )


def _evidence_rows(decision: Decision) -> list[EvidenceRow]:
    rows: list[EvidenceRow] = []
    for kind, items in ((_SUPPORTING, decision.evidence), (_COUNTER, decision.counter_evidence)):
        for item in items:
            rows.append(
                EvidenceRow(
                    id=item.id.value,
                    decision_id=decision.id.value,
                    kind=kind,
                    source=item.source,
                    category=item.category,
                    description=item.description,
                    confidence=item.confidence.value,
                    timestamp=item.timestamp,
                )
            )
    return rows


def _evidence_from_row(row: EvidenceRow) -> Evidence:
    return Evidence(
        source=row.source,
        category=row.category,
        description=row.description,
        confidence=Confidence(Decimal(row.confidence)),
        timestamp=row.timestamp,
        id=EvidenceId(row.id),
    )


def _to_row(decision: Decision) -> DecisionRow:
    return DecisionRow(
        id=decision.id.value,
        hypothesis=decision.hypothesis,
        probability=decision.probability.value,
        confidence=decision.confidence.value,
        status=decision.status.value,
        decision_type=decision.decision_type.value if decision.decision_type else None,
        expected_return=decision.expected_return,
        expected_drawdown=decision.expected_drawdown,
        expected_utility=decision.expected_utility,
        position_size=decision.position_size.value if decision.position_size else None,
        portfolio_impact=decision.portfolio_impact,
        explanation=decision.explanation,
        assumptions=list(decision.assumptions),
        invalidation_conditions=list(decision.invalidation_conditions),
        risk_assessment=_risk_to_json(decision.risk_assessment),
        review_history=[
            {"outcome": r.outcome.value, "at": r.at.isoformat(), "note": r.note}
            for r in decision.review_history
        ],
        created_at=decision.created_at,
        evidence=_evidence_rows(decision),
    )


def _from_row(row: DecisionRow) -> Decision:
    decision = Decision(
        hypothesis=row.hypothesis,
        probability=Probability(Decimal(row.probability)),
        confidence=Confidence(Decimal(row.confidence)),
        id=DecisionId(row.id),
        decision_type=DecisionType(row.decision_type) if row.decision_type else None,
        expected_return=Decimal(row.expected_return) if row.expected_return is not None else None,
        expected_drawdown=(
            Decimal(row.expected_drawdown) if row.expected_drawdown is not None else None
        ),
        expected_utility=(
            Decimal(row.expected_utility) if row.expected_utility is not None else None
        ),
        position_size=(
            PositionSize(Decimal(row.position_size)) if row.position_size is not None else None
        ),
        portfolio_impact=row.portfolio_impact,
        explanation=row.explanation,
        assumptions=tuple(row.assumptions),
        invalidation_conditions=tuple(row.invalidation_conditions),
        status=DecisionStatus(row.status),
        created_at=row.created_at,
        evidence=tuple(_evidence_from_row(e) for e in row.evidence if e.kind == _SUPPORTING),
        counter_evidence=tuple(_evidence_from_row(e) for e in row.evidence if e.kind == _COUNTER),
        risk_assessment=_risk_from_json(row.risk_assessment),
        review_history=tuple(
            ReviewRecord(
                outcome=DecisionStatus(r["outcome"]),
                at=datetime.fromisoformat(r["at"]),
                note=r["note"],
            )
            for r in row.review_history
        ),
    )
    # Reconstruction is not creation: discard the constructor's DecisionCreated event.
    decision.pull_events()
    return decision


class SqlDecisionRepository(DecisionRepository):
    """Persists the Decision aggregate with full lineage and audit records."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._sessions = session_factory

    def save(self, decision: Decision) -> None:
        with session_scope(self._sessions) as session:
            existing = session.get(DecisionRow, decision.id.value)
            action = "UPDATE" if existing is not None else "CREATE"
            if existing is not None:
                session.delete(existing)
                session.flush()
            row = _to_row(decision)
            session.add(row)
            write_audit(
                session,
                entity_type="decision",
                entity_id=decision.id.value,
                action=action,
                snapshot={"status": decision.status.value, "hypothesis": decision.hypothesis},
            )

    def get(self, decision_id: DecisionId) -> Decision | None:
        with session_scope(self._sessions) as session:
            row = session.get(DecisionRow, decision_id.value)
            return None if row is None else _from_row(row)
