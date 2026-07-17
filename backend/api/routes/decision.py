"""Decisions resource (SPEC-08 §Decisions).

Controllers contain no business logic; use cases orchestrate the
aggregate. The Decision stage stays deterministic and non-LLM
(SPEC-00, LLM Policy; ADR-0003).
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Request

from api.deps import Container, container, current_user, writer
from api.envelope import ok
from api.mappers import decision_out
from api.schemas import (
    DecisionCreateRequest,
    DecisionResponse,
    DecisionUpdateRequest,
    Envelope,
    EvidenceIn,
    Page,
)
from decision_kernel.application.use_cases import (
    CreateDecisionInput,
    EvidenceInput,
    UpdateDecisionInput,
)
from decision_kernel.domain.decision import DecisionStatus
from identity.domain.user import User
from risk.domain.risk_assessment import RiskAssessment, RiskLevel
from shared_kernel.identifiers import DecisionId
from shared_kernel.probability import Confidence

router = APIRouter(prefix="/decisions", tags=["decision"])


def _evidence_inputs(items: list[EvidenceIn]) -> tuple[EvidenceInput, ...]:
    return tuple(
        EvidenceInput(
            source=item.source,
            category=item.category,
            explanation=item.explanation,
            reliability=item.reliability,
            direction=item.direction,
            metadata=item.metadata,
        )
        for item in items
    )


@router.get("", summary="List decisions with pagination and status filter")
async def list_decisions(
    request: Request,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status: DecisionStatus | None = Query(default=None),
    services: Container = Depends(container),
    _user: User = Depends(current_user),
) -> Envelope[Page[DecisionResponse]]:
    page = services.decisions.list(limit=limit, offset=offset, status=status)
    return ok(
        request,
        Page[DecisionResponse](
            items=[decision_out(d) for d in page.items],
            total=page.total,
            limit=page.limit,
            offset=page.offset,
        ),
    )


@router.get("/{decision_id}", summary="Get a decision with full lineage")
async def get_decision(
    request: Request,
    decision_id: uuid.UUID,
    services: Container = Depends(container),
    _user: User = Depends(current_user),
) -> Envelope[DecisionResponse]:
    decision = services.decisions.get(DecisionId(decision_id))
    return ok(request, decision_out(decision))


@router.post("", status_code=201, summary="Create a decision draft")
async def create_decision(
    request: Request,
    body: DecisionCreateRequest,
    services: Container = Depends(container),
    _user: User = Depends(writer),
) -> Envelope[DecisionResponse]:
    decision = services.decisions.create(
        CreateDecisionInput(
            hypothesis=body.hypothesis,
            probability=body.probability,
            confidence=body.confidence,
            decision_type=body.decision_type,
            expected_return=body.expected_return,
            expected_drawdown=body.expected_drawdown,
            assumptions=tuple(body.assumptions),
            invalidation_conditions=tuple(body.invalidation_conditions),
            evidence=_evidence_inputs(list(body.evidence)),
        )
    )
    return ok(request, decision_out(decision))


@router.patch("/{decision_id}", summary="Update fields or request a lifecycle transition")
async def update_decision(
    request: Request,
    decision_id: uuid.UUID,
    body: DecisionUpdateRequest,
    services: Container = Depends(container),
    _user: User = Depends(writer),
) -> Envelope[DecisionResponse]:
    risk = None
    if body.risk_assessment is not None:
        ra = body.risk_assessment
        risk = RiskAssessment(
            var=ra.var,
            cvar=ra.cvar,
            max_drawdown=ra.max_drawdown,
            stress_score=ra.stress_score,
            liquidity_score=ra.liquidity_score,
            level=RiskLevel(ra.level),
            confidence=Confidence(ra.confidence),
        )
    decision = services.decisions.update(
        DecisionId(decision_id),
        UpdateDecisionInput(
            explanation=body.explanation,
            assumptions=tuple(body.assumptions) if body.assumptions is not None else None,
            invalidation_conditions=(
                tuple(body.invalidation_conditions)
                if body.invalidation_conditions is not None
                else None
            ),
            add_evidence=_evidence_inputs(list(body.add_evidence)),
            risk_assessment=risk,
            status=body.status,
            review_note=body.review_note,
        ),
    )
    return ok(request, decision_out(decision))
