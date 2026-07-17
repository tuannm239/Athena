"""Portfolios resource (SPEC-08 §Portfolios)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Request

from api.deps import Container, container, current_user, writer
from api.envelope import ok
from api.mappers import portfolio_out
from api.schemas import Envelope, Page, PortfolioCreateRequest, PortfolioResponse, PositionOut
from identity.domain.user import User
from shared_kernel.identifiers import PortfolioId

router = APIRouter(prefix="/portfolios", tags=["portfolio"])


@router.get("", summary="List the caller's portfolios")
async def list_portfolios(
    request: Request,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    services: Container = Depends(container),
    user: User = Depends(current_user),
) -> Envelope[Page[PortfolioResponse]]:
    page = services.portfolios.list(user.id, limit=limit, offset=offset)
    return ok(
        request,
        Page[PortfolioResponse](
            items=[portfolio_out(p) for p in page.items],
            total=page.total,
            limit=page.limit,
            offset=page.offset,
        ),
    )


@router.post("", status_code=201, summary="Create a portfolio")
async def create_portfolio(
    request: Request,
    body: PortfolioCreateRequest,
    services: Container = Depends(container),
    user: User = Depends(writer),
) -> Envelope[PortfolioResponse]:
    portfolio = services.portfolios.create(user.id, body.base_currency, body.cash)
    return ok(request, portfolio_out(portfolio))


@router.get("/{portfolio_id}", summary="Get one of the caller's portfolios")
async def get_portfolio(
    request: Request,
    portfolio_id: uuid.UUID,
    services: Container = Depends(container),
    user: User = Depends(current_user),
) -> Envelope[PortfolioResponse]:
    portfolio = services.portfolios.get_owned(PortfolioId(portfolio_id), user.id)
    return ok(request, portfolio_out(portfolio))


@router.get("/{portfolio_id}/positions", summary="List positions of a portfolio")
async def list_positions(
    request: Request,
    portfolio_id: uuid.UUID,
    services: Container = Depends(container),
    user: User = Depends(current_user),
) -> Envelope[list[PositionOut]]:
    portfolio = services.portfolios.get_owned(PortfolioId(portfolio_id), user.id)
    return ok(request, portfolio_out(portfolio).positions)
