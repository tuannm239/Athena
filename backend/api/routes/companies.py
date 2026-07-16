"""Companies resource (SPEC-08 §Companies).

Profile endpoint is live over the companies table (Executive Directive);
factors and research remain 501 until ALG-002 and the Research Copilot.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from api.deps import Container, container, current_user
from api.envelope import ok
from api.mappers import company_out
from api.routes._placeholder import NOT_IMPLEMENTED_RESPONSES, not_implemented
from api.schemas import CompanyResponse, Envelope
from identity.domain.user import User
from shared_kernel.exceptions import NotFoundError

router = APIRouter(prefix="/companies", tags=["company"], responses=NOT_IMPLEMENTED_RESPONSES)


@router.get("/{ticker}", summary="Company profile")
async def get_company(
    request: Request,
    ticker: str,
    services: Container = Depends(container),
    _user: User = Depends(current_user),
) -> Envelope[CompanyResponse]:
    company = services.companies.get_by_ticker(ticker)
    if company is None:
        raise NotFoundError(f"company not found: {ticker}")
    return ok(request, company_out(company))


@router.get("/{ticker}/factors", summary="Company factor values")
async def get_company_factors(ticker: str, _user: User = Depends(current_user)) -> None:
    not_implemented()


@router.get("/{ticker}/research", summary="Company research summaries")
async def get_company_research(ticker: str, _user: User = Depends(current_user)) -> None:
    not_implemented()
