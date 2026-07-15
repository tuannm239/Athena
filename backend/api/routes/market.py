"""Market Engine — regime, liquidity, breadth, volatility (SPEC-02)."""

from __future__ import annotations

from fastapi import APIRouter

from api.routes._placeholder import NOT_IMPLEMENTED_RESPONSES, not_implemented

router = APIRouter(prefix="/market", tags=["market"], responses=NOT_IMPLEMENTED_RESPONSES)


@router.get("/regime", summary="Current market regime assessment")
async def get_regime() -> None:
    not_implemented()
