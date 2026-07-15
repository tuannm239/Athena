"""Companies resource (SPEC-08 §Companies) — 501 until factor/company engines land.

Blocked on the companies-persistence ruling (GAP F17) and ALG-002.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from api.deps import current_user
from api.routes._placeholder import NOT_IMPLEMENTED_RESPONSES, not_implemented
from identity.domain.user import User

router = APIRouter(prefix="/companies", tags=["company"], responses=NOT_IMPLEMENTED_RESPONSES)


@router.get("/{ticker}", summary="Company profile")
async def get_company(ticker: str, _user: User = Depends(current_user)) -> None:
    not_implemented()


@router.get("/{ticker}/factors", summary="Company factor values")
async def get_company_factors(ticker: str, _user: User = Depends(current_user)) -> None:
    not_implemented()


@router.get("/{ticker}/research", summary="Company research summaries")
async def get_company_research(ticker: str, _user: User = Depends(current_user)) -> None:
    not_implemented()
