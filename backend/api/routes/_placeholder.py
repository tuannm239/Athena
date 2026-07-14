"""Shared placeholder behavior for endpoints scheduled in later sprints."""
from __future__ import annotations

from typing import NoReturn

from fastapi import HTTPException

NOT_IMPLEMENTED_RESPONSES: dict[int | str, dict[str, str]] = {
    501: {"description": "Not implemented — scheduled in a later sprint"}
}


def not_implemented() -> NoReturn:
    raise HTTPException(status_code=501, detail="Not implemented")
