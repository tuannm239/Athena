"""ATHENA API application factory.

Every business route is a Sprint 0 placeholder returning HTTP 501;
implementations arrive in their scheduled sprints (IMPLEMENTATION_PLAN.md).
"""

from __future__ import annotations

from fastapi import FastAPI

from api.routes import analysis, behavior, decision, market, portfolio, research, risk

API_V1_PREFIX = "/api/v1"


def create_app() -> FastAPI:
    app = FastAPI(
        title="ATHENA",
        summary="Financial Decision Intelligence Platform",
        version="0.1.0",
    )

    for module in (market, analysis, decision, portfolio, risk, behavior, research):
        app.include_router(module.router, prefix=API_V1_PREFIX)

    @app.get("/health", tags=["ops"], summary="Liveness probe")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
