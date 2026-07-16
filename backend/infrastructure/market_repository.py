"""MarketRepository adapters (SPEC-07: short-lived market context in Redis).

`InMemoryMarketRepository` backs tests and single-process deployments;
`RedisMarketRepository` is the production adapter with a TTL.
"""

from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal

from infrastructure.cache import RedisCache
from market.domain.market_context import MarketContext, Regime
from market.domain.repository import MarketRepository
from shared_kernel.probability import Confidence

_KEY = "athena:market:context"


class InMemoryMarketRepository(MarketRepository):
    def __init__(self) -> None:
        self._context: MarketContext | None = None

    def save_context(self, context: MarketContext) -> None:
        self._context = context

    def latest_context(self) -> MarketContext | None:
        return self._context


def _to_json(context: MarketContext) -> str:
    return json.dumps(
        {
            "regime": context.regime.value,
            "confidence": str(context.confidence.value),
            "liquidity_score": str(context.liquidity_score),
            "breadth_score": str(context.breadth_score),
            "volatility_score": str(context.volatility_score),
            "rotation_score": str(context.rotation_score),
            "timestamp": context.timestamp.isoformat(),
        }
    )


def _from_json(payload: str) -> MarketContext:
    data = json.loads(payload)
    return MarketContext(
        regime=Regime(data["regime"]),
        confidence=Confidence(Decimal(data["confidence"])),
        liquidity_score=Decimal(data["liquidity_score"]),
        breadth_score=Decimal(data["breadth_score"]),
        volatility_score=Decimal(data["volatility_score"]),
        rotation_score=Decimal(data["rotation_score"]),
        timestamp=datetime.fromisoformat(data["timestamp"]),
    )


class RedisMarketRepository(MarketRepository):
    """Short-lived market context (SPEC-07 §Redis); default TTL one day."""

    def __init__(self, cache: RedisCache, ttl_seconds: int = 86_400) -> None:
        self._cache = cache
        self._ttl = ttl_seconds

    def save_context(self, context: MarketContext) -> None:
        self._cache.set(_KEY, _to_json(context), ttl_seconds=self._ttl)

    def latest_context(self) -> MarketContext | None:
        payload = self._cache.get(_KEY)
        return None if payload is None else _from_json(payload)
