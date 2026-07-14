"""Decision Kernel — hypothesis, probability, utility, evidence, explanation.

The Decision stage is deterministic and non-LLM (SPEC-00, LLM Policy; ADR-0003).
"""
from __future__ import annotations

from fastapi import APIRouter

from api.routes._placeholder import NOT_IMPLEMENTED_RESPONSES, not_implemented

router = APIRouter(prefix="/decisions", tags=["decision"], responses=NOT_IMPLEMENTED_RESPONSES)


@router.get("", summary="List decisions with full lineage")
async def list_decisions() -> None:
    not_implemented()


@router.post("/evaluate", summary="Evaluate a decision hypothesis")
async def evaluate_decision() -> None:
    not_implemented()
