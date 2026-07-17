"""Standard response envelope and request-id middleware (SPEC-08)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, TypeVar

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from api.schemas import ApiError, Envelope
from infrastructure.metrics import Metrics
from infrastructure.observability import RequestTimer, get_logger

_access_log = get_logger("api.access")

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
    """Assigns a request id (honoring X-Request-ID), echoes it back,
    writes the access log and records HTTP metrics (Module 6)."""

    def __init__(self, app: Any, metrics: Metrics | None = None) -> None:
        super().__init__(app)
        self._metrics = metrics

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request.state.request_id = request.headers.get("X-Request-ID", uuid.uuid4().hex)
        timer = RequestTimer()
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        _access_log.info(
            "request",
            extra={
                "request_id": request.state.request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": timer.duration_ms,
            },
        )
        if self._metrics is not None:
            # Route template keeps label cardinality bounded; requests
            # that matched no route share one "unmatched" label.
            route = request.scope.get("route")
            template = getattr(route, "path", "unmatched")
            self._metrics.observe_request(
                method=request.method,
                path=str(template),
                status=response.status_code,
                seconds=timer.duration_ms / 1000,
            )
        return response
