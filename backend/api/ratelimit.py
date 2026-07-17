"""In-process rate limiting (ADR-0019).

Token buckets per client host, with a stricter bucket for auth
endpoints (login brute-force). Per-process only — the interim stance
until a shared Redis limiter is warranted; documented in ADR-0019.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse, Response

from api.envelope import error_body

_AUTH_PREFIX = "/api/v1/auth/"
_EXEMPT = ("/health", "/metrics")


@dataclass
class _Bucket:
    capacity: float
    tokens: float
    refill_per_second: float
    updated: float

    def take(self, now: float) -> bool:
        self.tokens = min(
            self.capacity, self.tokens + (now - self.updated) * self.refill_per_second
        )
        self.updated = now
        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False


@dataclass
class RateLimiter:
    per_minute: int
    auth_per_minute: int
    clock: Callable[[], float] = field(default=time.monotonic)
    _buckets: dict[tuple[str, str], _Bucket] = field(default_factory=dict)

    def allow(self, client: str, path: str) -> bool:
        if path.startswith(_EXEMPT):
            return True
        scope = "auth" if path.startswith(_AUTH_PREFIX) else "api"
        limit = self.auth_per_minute if scope == "auth" else self.per_minute
        if limit <= 0:
            return True
        key = (client, scope)
        now = self.clock()
        bucket = self._buckets.get(key)
        if bucket is None:
            bucket = _Bucket(
                capacity=float(limit),
                tokens=float(limit),
                refill_per_second=limit / 60,
                updated=now,
            )
            self._buckets[key] = bucket
        return bucket.take(now)


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: Any, limiter: RateLimiter) -> None:
        super().__init__(app)
        self._limiter = limiter

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        client = request.client.host if request.client else "unknown"
        if not self._limiter.allow(client, request.url.path):
            return JSONResponse(
                status_code=429,
                content=error_body(request, "RateLimited", "too many requests; slow down"),
                headers={"Retry-After": "60"},
            )
        return await call_next(request)
