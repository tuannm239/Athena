"""ATHENA API application factory (SPEC-08).

Implemented resources: auth, decisions, portfolios. Market, companies
and backtests expose their SPEC-08 paths returning 501 until their
engines land (see IMPLEMENTATION_BACKLOG.md). Operations surface:
/health (liveness), /health/full (component dashboard), /metrics
(Prometheus exposition — ADR-0018).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request, Response
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from api.deps import build_container, container
from api.envelope import RequestIdMiddleware
from api.errors import register_error_handlers
from api.ratelimit import RateLimiter, RateLimitMiddleware
from api.routes import auth, backtests, companies, decision, market, portfolio
from infrastructure.config import Settings
from infrastructure.metrics import Metrics
from infrastructure.observability import configure_logging

API_V1_PREFIX = "/api/v1"
APP_VERSION = "0.4.0"


def _database_status(sessions: sessionmaker[Session]) -> str:
    try:
        with sessions() as session:
            session.execute(text("SELECT 1"))
        return "ok"
    except Exception as error:  # noqa: BLE001 — dashboard reports, never raises
        return f"unavailable: {type(error).__name__}"


def _redis_status(url: str) -> str:
    try:
        import redis

        client = redis.Redis.from_url(url, socket_connect_timeout=1, socket_timeout=1)
        client.ping()
        return "ok"
    except Exception as error:  # noqa: BLE001 — dashboard reports, never raises
        return f"unavailable: {type(error).__name__}"


def _snapshots_status(duckdb_dir: str) -> str:
    path = Path(duckdb_dir)
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".health-probe"
        probe.write_text("ok")
        probe.unlink()
        return "ok"
    except OSError as error:
        return f"unavailable: {type(error).__name__}"


def _market_data_status(container: Any) -> dict[str, Any]:
    """Operator view of persisted VN prices: storage backend + row count.

    Public (no auth) so an operator can confirm from a browser whether the
    market sync has populated data and which snapshot backend is in use —
    without shell access or reading logs. Read-only; never raises.
    """
    from data_pipeline.application.sync import PRICES_DATASET
    from data_pipeline.application.use_cases import DataPipelineUseCases
    from infrastructure.db.repositories.dataset_catalog import SqlDatasetCatalog
    from infrastructure.sql_snapshot_store import build_snapshot_store

    cfg = container.settings
    result: dict[str, Any] = {"snapshot_backend": cfg.snapshot_backend, "price_rows": 0}
    try:
        pipeline = DataPipelineUseCases(
            catalog=SqlDatasetCatalog(container.sessions),
            snapshots=build_snapshot_store(cfg, container.sessions),
        )
        try:
            result["price_rows"] = pipeline.read_published(PRICES_DATASET).height
        except Exception as error:  # noqa: BLE001 — no readable snapshot
            result["price_rows"] = 0
            result["read_detail"] = f"{type(error).__name__}: {error}"
    except Exception as error:  # noqa: BLE001 — never break the health probe
        result["error"] = f"{type(error).__name__}: {error}"
    result["has_prices"] = result["price_rows"] > 0
    return result


def create_app(
    settings: Settings | None = None,
    session_factory: sessionmaker[Session] | None = None,
) -> FastAPI:
    configure_logging()
    app = FastAPI(
        title="ATHENA",
        summary="Financial Decision Intelligence Platform",
        version=APP_VERSION,
    )
    metrics = Metrics(version=APP_VERSION)
    app.state.container = build_container(settings=settings, session_factory=session_factory)
    cfg = app.state.container.settings
    cfg.ensure_safe_for_environment()  # fail fast on dev secrets in production
    app.state.metrics = metrics
    # Middleware order (outermost last-added): request-id wraps rate limiting
    # so even 429 responses carry an id and land in the access log/metrics.
    app.add_middleware(
        RateLimitMiddleware,
        limiter=RateLimiter(
            per_minute=cfg.rate_limit_per_minute,
            auth_per_minute=cfg.auth_rate_limit_per_minute,
        ),
    )
    app.add_middleware(RequestIdMiddleware, metrics=metrics)
    register_error_handlers(app)

    for module in (auth, decision, portfolio, companies, market, backtests):
        app.include_router(module.router, prefix=API_V1_PREFIX)

    @app.get("/health", tags=["ops"], summary="Liveness probe")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health/full", tags=["ops"], summary="Component health dashboard")
    async def health_full(request: Request) -> dict[str, Any]:
        deps = container(request)
        components = {
            "database": _database_status(deps.sessions),
            "redis": _redis_status(deps.settings.redis_url),
            "snapshots": _snapshots_status(deps.settings.duckdb_dir),
        }
        status = "ok" if all(value == "ok" for value in components.values()) else "degraded"
        return {
            "status": status,
            "version": APP_VERSION,
            "pilot_mode": deps.settings.pilot_mode,
            "components": components,
            "market_data": _market_data_status(deps),
        }

    @app.get("/pilot/status", tags=["ops"], summary="Pilot-mode posture")
    async def pilot_status(request: Request) -> dict[str, Any]:
        """Reports the pilot-mode operating posture (Phase 5, W6). Athena is a
        decision-support system: it generates Decision Objects only, executes
        no trades, integrates no broker, and requires human approval — these
        are structural guarantees, surfaced here for operators."""
        deps = container(request)
        return {
            "pilot_mode": deps.settings.pilot_mode,
            "environment": deps.settings.environment,
            "read_only_market_access": True,
            "order_execution": False,
            "broker_integration": False,
            "human_approval_required": True,
            "audit_trail": True,
        }

    @app.get("/metrics", tags=["ops"], summary="Prometheus metrics", include_in_schema=False)
    async def metrics_endpoint() -> Response:
        body, content_type = metrics.render()
        return Response(content=body, media_type=content_type)

    return app


app = create_app()
