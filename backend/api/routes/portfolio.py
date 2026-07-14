"""Portfolio Engine — allocation, exposure, diversification, sizing (SPEC-02)."""
from __future__ import annotations

from fastapi import APIRouter

from api.routes._placeholder import NOT_IMPLEMENTED_RESPONSES, not_implemented

router = APIRouter(prefix="/portfolio", tags=["portfolio"], responses=NOT_IMPLEMENTED_RESPONSES)


@router.get("", summary="Current portfolio state")
async def get_portfolio() -> None:
    not_implemented()


@router.post("/optimize", summary="Optimize portfolio under constraints")
async def optimize_portfolio() -> None:
    not_implemented()
