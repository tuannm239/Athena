"""Risk Engine — VaR, CVaR, stress tests, drawdown (SPEC-02).

Risk is computed before any return-seeking optimization (Constitution).
"""

from __future__ import annotations

from fastapi import APIRouter

from api.routes._placeholder import NOT_IMPLEMENTED_RESPONSES, not_implemented

router = APIRouter(prefix="/risk", tags=["risk"], responses=NOT_IMPLEMENTED_RESPONSES)


@router.get("/report", summary="Portfolio risk report")
async def get_risk_report() -> None:
    not_implemented()
