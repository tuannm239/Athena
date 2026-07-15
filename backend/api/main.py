"""ATHENA API application factory (SPEC-08).

Implemented resources: auth, decisions, portfolios. Market, companies
and backtests expose their SPEC-08 paths returning 501 until their
engines land (see IMPLEMENTATION_BACKLOG.md).
"""

from __future__ import annotations

from fastapi import FastAPI
from sqlalchemy.orm import Session, sessionmaker

from api.deps import build_container
from api.envelope import RequestIdMiddleware
from api.errors import register_error_handlers
from api.routes import auth, backtests, companies, decision, market, portfolio
from infrastructure.config import Settings

API_V1_PREFIX = "/api/v1"


def create_app(
    settings: Settings | None = None,
    session_factory: sessionmaker[Session] | None = None,
) -> FastAPI:
    app = FastAPI(
        title="ATHENA",
        summary="Financial Decision Intelligence Platform",
        version="0.3.0",
    )
    app.state.container = build_container(settings=settings, session_factory=session_factory)
    app.add_middleware(RequestIdMiddleware)
    register_error_handlers(app)

    for module in (auth, decision, portfolio, companies, market, backtests):
        app.include_router(module.router, prefix=API_V1_PREFIX)

    @app.get("/health", tags=["ops"], summary="Liveness probe")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
