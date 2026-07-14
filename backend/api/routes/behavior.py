"""Behavior Engine — bias detection, decision review, investor profile (SPEC-02)."""
from __future__ import annotations

from fastapi import APIRouter

from api.routes._placeholder import NOT_IMPLEMENTED_RESPONSES, not_implemented

router = APIRouter(prefix="/behavior", tags=["behavior"], responses=NOT_IMPLEMENTED_RESPONSES)


@router.get("/overrides", summary="Triggered behavioral overrides")
async def list_overrides() -> None:
    not_implemented()
