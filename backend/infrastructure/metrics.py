"""Prometheus metrics (Phase 2, Module 6; ADR-0018).

One `Metrics` instance per application (its own `CollectorRegistry`,
so test apps never collide). HTTP metrics are recorded by the API
middleware against the *route template* (bounded label cardinality);
`render()` produces the Prometheus exposition format for `/metrics`.
"""

from __future__ import annotations

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

_DURATION_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)


class Metrics:
    """Application metrics registry and instruments."""

    def __init__(self, version: str) -> None:
        self.registry = CollectorRegistry()
        self.http_requests = Counter(
            "athena_http_requests_total",
            "HTTP requests by method, route template and status code.",
            ("method", "path", "status"),
            registry=self.registry,
        )
        self.http_duration = Histogram(
            "athena_http_request_duration_seconds",
            "HTTP request latency by method and route template.",
            ("method", "path"),
            registry=self.registry,
            buckets=_DURATION_BUCKETS,
        )
        self.app_info = Gauge(
            "athena_app_info",
            "Static application metadata (value is always 1).",
            ("version",),
            registry=self.registry,
        )
        self.app_info.labels(version=version).set(1)

    def observe_request(self, *, method: str, path: str, status: int, seconds: float) -> None:
        self.http_requests.labels(method=method, path=path, status=str(status)).inc()
        self.http_duration.labels(method=method, path=path).observe(seconds)

    def render(self) -> tuple[bytes, str]:
        """Exposition body and content type for the /metrics endpoint."""
        return generate_latest(self.registry), CONTENT_TYPE_LATEST
