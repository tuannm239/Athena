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


def _empty_fundamentals(ticker: str, exchange: str, sector: str) -> dict[str, object]:
    """Honest-empty payload (nulls) — shown until a company sync runs; never fake."""
    ratio_keys = (
        "roe",
        "roa",
        "gross_margin",
        "operating_margin",
        "net_margin",
        "debt_to_equity",
        "current_ratio",
        "free_cash_flow",
        "eps",
        "bvps",
        "pe",
        "pb",
        "ev_ebitda",
    )
    return {
        "ticker": ticker,
        "exchange": exchange,
        "sector": sector,
        "ratios": {k: None for k in ratio_keys},
        "quality_score": None,
        "valuation_score": None,
        "growth_score": None,
        "revenue_growth_yoy": None,
        "eps_growth_yoy": None,
    }


@router.get("/{ticker}/fundamentals", summary="Company fundamentals (ratios + scores)")
async def get_company_fundamentals(
    request: Request,
    ticker: str,
    services: Container = Depends(container),
    _user: User = Depends(current_user),
) -> Envelope[dict[str, object]]:
    key = ticker.upper()
    payload = services.company_fundamentals.get(key)
    if payload is not None:
        return ok(request, payload)
    # Not yet synced → honest empty (nulls), enriched with the profile if known.
    company = services.companies.get_by_ticker(key)
    exchange = company.exchange if company else ""
    sector = company.sector if company else ""
    return ok(request, _empty_fundamentals(key, exchange, sector))


@router.get("/{ticker}/factors", summary="Company factor values")
async def get_company_factors(ticker: str, _user: User = Depends(current_user)) -> None:
    not_implemented()


@router.get("/{ticker}/research", summary="Company research summaries")
async def get_company_research(ticker: str, _user: User = Depends(current_user)) -> None:
    not_implemented()
