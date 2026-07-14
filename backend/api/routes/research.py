"""Research Copilot — structured research summaries (SPEC-01, MVP scope).

LLM-assisted surfaces only; never decisions (SPEC-05).
"""
from __future__ import annotations

from fastapi import APIRouter

from api.routes._placeholder import NOT_IMPLEMENTED_RESPONSES, not_implemented

router = APIRouter(prefix="/research", tags=["research"], responses=NOT_IMPLEMENTED_RESPONSES)


@router.post("/summaries", summary="Generate a structured research summary")
async def create_summary() -> None:
    not_implemented()
