"""Company Engine — fundamentals, valuation, quality, catalysts (SPEC-02)."""
from __future__ import annotations

from fastapi import APIRouter

from api.routes._placeholder import NOT_IMPLEMENTED_RESPONSES, not_implemented

router = APIRouter(prefix="/analysis", tags=["analysis"], responses=NOT_IMPLEMENTED_RESPONSES)


@router.get("/companies", summary="Probabilistic company assessments")
async def list_company_assessments() -> None:
    not_implemented()


@router.get("/sectors", summary="Probabilistic sector assessments")
async def list_sector_assessments() -> None:
    not_implemented()
