"""DNSE market-data adapter — implements the SDK `PriceProvider` port.

Adapter only (ADR-0003/0017): it maps DNSE chart responses to `PriceBar`s and
implements the *existing* provider interface, so the Market Engine, Data
Pipeline, Feature Store and every downstream engine consume it unchanged. Both
stocks and Vietnamese indices (VNINDEX/VN30/…) are covered, feeding the same
price dataset the Market snapshot reads.

Resilience (retry/backoff, rate limit, TTL cache, health) is composed from the
existing Module-2 stack via `create_dnse_price_provider` — not re-implemented.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone

from providers.connectors.dnse.client import DnseMarketClient
from providers.connectors.dnse.models import parse_udf_bars
from providers.connectors.resilience import (
    HealthMonitor,
    RetryPolicy,
    TokenBucketRateLimiter,
    TtlCache,
)
from providers.connectors.resilient import ResilientPriceProvider
from providers.sdk.models import PriceBar

# Index codes DNSE serves via the index chart route (vs the stock route).
INDEX_SYMBOLS = frozenset({"VNINDEX", "VN30", "HNXINDEX", "HNX30", "HNXUPCOMINDEX", "UPCOMINDEX"})

# Be a courteous client: ~2 req/s with a small burst, cached for an hour.
_DEFAULT_RATE_PER_SECOND = 2.0
_DEFAULT_BURST = 5.0
_DEFAULT_CACHE_TTL = 3600.0

_DAILY_RESOLUTION = "1D"


def _epoch(day: date) -> int:
    return int(datetime(day.year, day.month, day.day, tzinfo=timezone.utc).timestamp())


@dataclass(frozen=True)
class DnseProvider:
    """Raw DNSE price adapter (no resilience). Implements PriceProvider."""

    client: DnseMarketClient

    def daily_bars(self, ticker: str, start: date, end: date) -> tuple[PriceBar, ...]:
        symbol = ticker.upper()
        payload = self.client.ohlc(
            symbol,
            _epoch(start),
            _epoch(end) + 86_400,  # inclusive of the end day
            _DAILY_RESOLUTION,
            is_index=symbol in INDEX_SYMBOLS,
        )
        return parse_udf_bars(symbol, payload, start, end)


def create_dnse_price_provider(*, client: DnseMarketClient | None = None) -> ResilientPriceProvider:
    """Production-ready resilient DNSE price provider (OHLCV incl. VNINDEX/VN30).

    The DNSE client already retries transient failures with backoff (spec §9),
    so the resilient decorator here adds only rate limiting, a TTL cache and
    health tracking (retry disabled to avoid double-retrying permanent errors).
    """
    return ResilientPriceProvider(
        inner=DnseProvider(client=client or DnseMarketClient.from_env()),
        retry=RetryPolicy(max_attempts=1),
        limiter=TokenBucketRateLimiter(
            rate_per_second=_DEFAULT_RATE_PER_SECOND, capacity=_DEFAULT_BURST
        ),
        cache=TtlCache(ttl_seconds=_DEFAULT_CACHE_TTL),
        health=HealthMonitor(name="dnse-price"),
    )
