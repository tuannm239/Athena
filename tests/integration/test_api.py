"""Integration tests — API skeleton (Sprint 0).

Verifies the Sprint 0 gates: the app builds, Swagger/OpenAPI loads,
and every placeholder business route returns HTTP 501.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import create_app

client = TestClient(create_app())


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_swagger_ui_loads() -> None:
    assert client.get("/docs").status_code == 200


def test_openapi_schema_loads() -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert response.json()["info"]["title"] == "ATHENA"


PLACEHOLDER_ROUTES: tuple[tuple[str, str], ...] = (
    ("GET", "/api/v1/market/regime"),
    ("GET", "/api/v1/analysis/companies"),
    ("GET", "/api/v1/analysis/sectors"),
    ("GET", "/api/v1/decisions"),
    ("POST", "/api/v1/decisions/evaluate"),
    ("GET", "/api/v1/portfolio"),
    ("POST", "/api/v1/portfolio/optimize"),
    ("GET", "/api/v1/risk/report"),
    ("GET", "/api/v1/behavior/overrides"),
    ("POST", "/api/v1/research/summaries"),
)


def test_every_placeholder_route_returns_501() -> None:
    for method, path in PLACEHOLDER_ROUTES:
        response = client.request(method, path)
        assert response.status_code == 501, (method, path, response.status_code)


def test_placeholder_routes_are_in_openapi_schema() -> None:
    paths = client.get("/openapi.json").json()["paths"]
    for method, path in PLACEHOLDER_ROUTES:
        assert path in paths, path
        assert method.lower() in paths[path], (method, path)
