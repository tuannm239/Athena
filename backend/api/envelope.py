"""Standard response envelope and request-id middleware (SPEC-08)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, TypeVar

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from api.schemas import ApiError, Envelope

T = TypeVar("T")


def request_id_of(request: Request) -> str:
    return str(getattr(request.state, "request_id", "unknown"))


def ok(request: Request, data: T) -> Envelope[T]:
    return Envelope[T](
        request_id=request_id_of(request),
        timestamp=datetime.now(timezone.utc),
        status="ok",
        data=data,
    )


def error_body(request: Request, code: str, detail: str) -> dict[str, Any]:
    envelope: Envelope[None] = Envelope(
        request_id=request_id_of(request),
        timestamp=datetime.now(timezone.utc),
        status="error",
        errors=[ApiError(code=code, detail=detail)],
    )
    return envelope.model_dump(mode="json")


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Assigns a request id (honoring X-Request-ID) and echoes it back."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request.state.request_id = request.headers.get("X-Request-ID", uuid.uuid4().hex)
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response
