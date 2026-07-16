"""Resilient provider decorator (Phase 2, Module 2).

Wraps any price provider with retries, rate limiting, caching and
health monitoring — composition, not inheritance, so every underlying
adapter stays independently testable and replaceable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from providers.connectors.resilience import (
    HealthMonitor,
    ProviderCallError,
    RetryPolicy,
    TokenBucketRateLimiter,
    TtlCache,
)
from providers.sdk.models import PriceBar, ProviderStatus
from providers.sdk.ports import PriceProvider


@dataclass
class ResilientPriceProvider:
    """PriceProvider decorator: cache → rate limit → retry → health."""

    inner: PriceProvider
    retry: RetryPolicy = field(default_factory=RetryPolicy)
    limiter: TokenBucketRateLimiter | None = None
    cache: TtlCache | None = None
    health: HealthMonitor = field(default_factory=lambda: HealthMonitor(name="price"))

    def daily_bars(self, ticker: str, start: date, end: date) -> tuple[PriceBar, ...]:
        key = f"{ticker}:{start}:{end}"
        if self.cache is not None:
            cached = self.cache.get(key)
            if cached is not None:
                assert isinstance(cached, tuple)
                return cached
        if self.limiter is not None and not self.limiter.try_acquire():
            raise ProviderCallError(f"rate limit exceeded for {self.health.name}")
        try:
            bars = self.retry.execute(lambda: self.inner.daily_bars(ticker, start, end))
        except ProviderCallError as exc:
            self.health.record_failure(str(exc))
            raise
        self.health.record_success()
        if self.cache is not None:
            self.cache.put(key, bars)
        return bars

    def status(self) -> ProviderStatus:
        return self.health.status()
