"""Investment universe management (editable `watchlist_universe`).

Read for any authenticated user; writes require ANALYST/ADMIN. The sync layer
reads active rows from the same table, so edits here change what
`athena sync universe` covers — no provider/code change needed.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from api.deps import Container, container, current_user, writer
from api.envelope import ok
from api.mappers import universe_out
from api.schemas import (
    Envelope,
    UniverseEntryResponse,
    UniversePatchRequest,
    UniverseUpsertRequest,
)
from data_pipeline.universe import SyncLevel, UniverseEntry
from identity.domain.user import User
from shared_kernel.exceptions import NotFoundError

router = APIRouter(prefix="/universe", tags=["universe"])


def _parse_level(value: str) -> SyncLevel:
    try:
        return SyncLevel(value.strip().upper())
    except ValueError as error:
        raise ValueError(f"invalid sync_level: {value!r}") from error


@router.get("", summary="List the investment universe")
async def list_universe(
    request: Request,
    services: Container = Depends(container),
    _user: User = Depends(current_user),
) -> Envelope[list[UniverseEntryResponse]]:
    return ok(request, [universe_out(e) for e in services.universe.all()])


@router.post("", summary="Add or update a universe symbol")
async def upsert_symbol(
    request: Request,
    body: UniverseUpsertRequest,
    services: Container = Depends(container),
    _user: User = Depends(writer),
) -> Envelope[UniverseEntryResponse]:
    entry = UniverseEntry(
        symbol=body.symbol.strip().upper(),
        sector=body.sector.strip().upper(),
        sync_level=_parse_level(body.sync_level),
        is_active=body.is_active,
    )
    services.universe.upsert(entry)
    stored = services.universe.get(entry.symbol)
    return ok(request, universe_out(stored or entry))


@router.patch("/{symbol}", summary="Edit a universe symbol (level / active)")
async def patch_symbol(
    request: Request,
    symbol: str,
    body: UniversePatchRequest,
    services: Container = Depends(container),
    _user: User = Depends(writer),
) -> Envelope[UniverseEntryResponse]:
    key = symbol.strip().upper()
    current = services.universe.get(key)
    if current is None:
        raise NotFoundError(f"symbol not in universe: {key}")
    updated = UniverseEntry(
        symbol=key,
        sector=current.sector,
        sync_level=_parse_level(body.sync_level) if body.sync_level else current.sync_level,
        is_active=body.is_active if body.is_active is not None else current.is_active,
    )
    services.universe.upsert(updated)
    return ok(request, universe_out(updated))


@router.delete("/{symbol}", summary="Remove a symbol from the universe")
async def delete_symbol(
    request: Request,
    symbol: str,
    services: Container = Depends(container),
    _user: User = Depends(writer),
) -> Envelope[dict[str, bool]]:
    key = symbol.strip().upper()
    removed = services.universe.remove(key)
    if not removed:
        raise NotFoundError(f"symbol not in universe: {key}")
    return ok(request, {"removed": True})
