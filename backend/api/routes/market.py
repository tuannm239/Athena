"""Market resource (SPEC-08 §Market).

Regime endpoints (`/context`, `/regime`, `/sectors`) return 501 until Market
Regime Detection (ALG-001) lands. The Vietnam market **snapshot** is live: it
reads the Data Pipeline's persisted prices (read model) and serves the indices,
breadth, movers and liquidity the Market page and dashboard widgets consume.
The controller holds no market logic and never touches a provider/vnstock — it
delegates to the wired `VnMarketSnapshotQuery` and maps the view to the schema.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from api.deps import Container, container, current_user
from api.envelope import ok
from api.mappers import vn_snapshot_out
from api.routes._placeholder import NOT_IMPLEMENTED_RESPONSES, not_implemented
from api.schemas import Envelope, VnMarketSnapshotResponse
from identity.domain.user import User

router = APIRouter(prefix="/market", tags=["market"], responses=NOT_IMPLEMENTED_RESPONSES)


@router.get("/vn/snapshot", summary="Vietnam market snapshot (persisted prices)")
async def vn_snapshot(
    request: Request,
    services: Container = Depends(container),
    _user: User = Depends(current_user),
) -> Envelope[VnMarketSnapshotResponse]:
    """Indices, breadth, movers and liquidity derived from the latest published
    prices. Returns an empty snapshot (not sample values) when no data is synced."""
    return ok(request, vn_snapshot_out(services.market_snapshot.snapshot()))


@router.get("/context", summary="Current market context (SPEC-05 Outputs)")
async def get_context(_user: User = Depends(current_user)) -> None:
    not_implemented()


@router.get("/regime", summary="Current market regime assessment")
async def get_regime(_user: User = Depends(current_user)) -> None:
    not_implemented()


@router.get("/sectors", summary="Sector assessments")
async def get_sectors(_user: User = Depends(current_user)) -> None:
    not_implemented()
