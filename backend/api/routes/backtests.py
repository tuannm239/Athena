"""Backtesting resource (SPEC-08 §Backtesting) — 501 until ALG-013.

Also blocked on RFC-0017 (Decision DSL) for strategy rule inputs.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends

from api.deps import current_user
from api.routes._placeholder import NOT_IMPLEMENTED_RESPONSES, not_implemented
from identity.domain.user import User

router = APIRouter(prefix="/backtests", tags=["backtest"], responses=NOT_IMPLEMENTED_RESPONSES)


@router.post("", summary="Run a backtest")
async def create_backtest(_user: User = Depends(current_user)) -> None:
    not_implemented()


@router.get("/{backtest_id}", summary="Get backtest results")
async def get_backtest(backtest_id: uuid.UUID, _user: User = Depends(current_user)) -> None:
    not_implemented()
