"""Market resource (SPEC-08 §Market) — contract in place, ALG-001 pending.

Endpoints return 501 until Market Regime Detection (ALG-001) lands;
the response contract is already published via MarketContextResponse.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from api.deps import current_user
from api.routes._placeholder import NOT_IMPLEMENTED_RESPONSES, not_implemented
from identity.domain.user import User

router = APIRouter(prefix="/market", tags=["market"], responses=NOT_IMPLEMENTED_RESPONSES)


@router.get("/context", summary="Current market context (SPEC-05 Outputs)")
async def get_context(_user: User = Depends(current_user)) -> None:
    not_implemented()


@router.get("/regime", summary="Current market regime assessment")
async def get_regime(_user: User = Depends(current_user)) -> None:
    not_implemented()


@router.get("/sectors", summary="Sector assessments")
async def get_sectors(_user: User = Depends(current_user)) -> None:
    not_implemented()
