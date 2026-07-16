"""Connector resilience primitives (Phase 2, Module 2).

Retries with exponential backoff, token-bucket rate limiting, TTL
caching and provider health monitoring. Clocks and sleepers are
injectable so every behavior is deterministic under test.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TypeVar

from providers.sdk.models import ProviderStatus
from shared_kernel.exceptions import DomainError

T = TypeVar("T")


class ProviderCallError(DomainError):
    """A provider call failed after all retries."""


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    """Exponential backoff: base_delay × 2^attempt, up to max_attempts."""

    max_attempts: int = 3
    base_delay_seconds: float = 0.5

    def execute(
        self,
        operation: Callable[[], T],
        *,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> T:
        last_error: Exception | None = None
        for attempt in range(self.max_attempts):
            try:
                return operation()
            except Exception as exc:  # adapters wrap any transport error
                last_error = exc
                if attempt < self.max_attempts - 1:
                    sleeper(self.base_delay_seconds * (2**attempt))
        raise ProviderCallError(
            f"operation failed after {self.max_attempts} attempts: {last_error}"
        ) from last_error


@dataclass
class TokenBucketRateLimiter:
    """Classic token bucket; `clock` injectable for deterministic tests."""

    rate_per_second: float
    capacity: float
    clock: Callable[[], float] = time.monotonic
    _tokens: float = field(init=False)
    _updated: float = field(init=False)

    def __post_init__(self) -> None:
        self._tokens = self.capacity
        self._updated = self.clock()

    def try_acquire(self, tokens: float = 1.0) -> bool:
        now = self.clock()
        self._tokens = min(
            self.capacity, self._tokens + (now - self._updated) * self.rate_per_second
        )
        self._updated = now
        if self._tokens >= tokens:
            self._tokens -= tokens
            return True
        return False


@dataclass
class TtlCache:
    """In-process TTL cache for provider responses (Module 2 caching)."""

    ttl_seconds: float
    clock: Callable[[], float] = time.monotonic
    _store: dict[str, tuple[float, object]] = field(default_factory=dict)

    def get(self, key: str) -> object | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        stored_at, value = entry
        if self.clock() - stored_at > self.ttl_seconds:
            del self._store[key]
            return None
        return value

    def put(self, key: str, value: object) -> None:
        self._store[key] = (self.clock(), value)


@dataclass
class HealthMonitor:
    """Consecutive-failure health tracking (Module 2 monitoring)."""

    name: str
    unhealthy_after: int = 3
    _consecutive_failures: int = field(default=0, init=False)
    _last_success: datetime | None = field(default=None, init=False)
    _detail: str = field(default="", init=False)

    def record_success(self) -> None:
        self._consecutive_failures = 0
        self._last_success = datetime.now(timezone.utc)
        self._detail = ""

    def record_failure(self, reason: str) -> None:
        self._consecutive_failures += 1
        self._detail = reason

    @property
    def healthy(self) -> bool:
        return self._consecutive_failures < self.unhealthy_after

    def status(self) -> ProviderStatus:
        return ProviderStatus(
            name=self.name,
            healthy=self.healthy,
            consecutive_failures=self._consecutive_failures,
            last_success_at=self._last_success,
            detail=self._detail,
        )
