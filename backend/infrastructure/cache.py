"""Redis adapter — cache and idempotency keys (SPEC-07, Redis).

Only ephemeral state lives here: caches, idempotency keys, short-lived
pipeline state. Nothing in Redis is a system of record.
"""

from __future__ import annotations

import redis
from redis.backoff import ExponentialBackoff
from redis.retry import Retry


class RedisCache:
    """Thin typed wrapper over redis-py for the two approved use cases.

    Connection settings are tuned for a managed, TLS-terminated Redis such
    as Upstash: `redis.Redis.from_url` reads the scheme, so a `rediss://`
    URL negotiates TLS automatically — no code change needed. A bounded
    connection pool (created implicitly by `from_url`), short socket
    timeouts, periodic health checks, and a retry-with-exponential-backoff
    policy keep the adapter resilient to the transient drops that serverless
    Redis endpoints exhibit, without ever blocking a request indefinitely.
    """

    def __init__(self, url: str) -> None:
        self._client: redis.Redis = redis.Redis.from_url(
            url,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            socket_keepalive=True,
            # Recycle idle connections before a managed endpoint reaps them.
            health_check_interval=30,
            # Retry transient timeouts/disconnects a few times before failing.
            retry=Retry(ExponentialBackoff(cap=2.0, base=0.1), retries=3),
            retry_on_timeout=True,
        )

    def get(self, key: str) -> str | None:
        value = self._client.get(key)
        return None if value is None else str(value)

    def set(self, key: str, value: str, ttl_seconds: int) -> None:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive (Redis holds ephemeral state only)")
        self._client.set(key, value, ex=ttl_seconds)

    def delete(self, key: str) -> None:
        self._client.delete(key)

    def acquire_idempotency_key(self, key: str, ttl_seconds: int) -> bool:
        """Set-if-absent; returns True when this caller owns the key."""
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        return bool(self._client.set(key, "1", nx=True, ex=ttl_seconds))

    def ping(self) -> bool:
        try:
            return bool(self._client.ping())
        except redis.RedisError:
            return False
