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
    app.state.metrics = metrics
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
        return {"status": status, "version": APP_VERSION, "components": components}

    @app.get("/metrics", tags=["ops"], summary="Prometheus metrics", include_in_schema=False)
    async def metrics_endpoint() -> Response:
        body, content_type = metrics.render()
        return Response(content=body, media_type=content_type)

    return app


app = create_app()
