"""Domain error → HTTP mapping (SPEC-08 §Error Codes).

400 ValidationError · 401 Unauthorized · 403 Forbidden · 404 NotFound ·
409 Conflict · 422 BusinessRuleViolation · 500 InternalError
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import JSONResponse

from api.envelope import error_body
from decision_kernel.domain.decision import InvalidDecisionTransition
from identity.application.ports import AuthenticationError, AuthorizationError
from shared_kernel.exceptions import ConflictError, DomainError, NotFoundError

_HTTP_CODE_NAMES = {
    400: "ValidationError",
    401: "Unauthorized",
    403: "Forbidden",
    404: "NotFound",
    405: "MethodNotAllowed",
    409: "Conflict",
    422: "BusinessRuleViolation",
    501: "NotImplemented",
}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=400, content=error_body(request, "ValidationError", str(exc.errors()))
        )

    @app.exception_handler(AuthenticationError)
    async def _auth(request: Request, exc: AuthenticationError) -> JSONResponse:
        return JSONResponse(
            status_code=401, content=error_body(request, "Unauthorized", str(exc) or "unauthorized")
        )

    @app.exception_handler(AuthorizationError)
    async def _forbidden(request: Request, exc: AuthorizationError) -> JSONResponse:
        return JSONResponse(
            status_code=403, content=error_body(request, "Forbidden", str(exc) or "forbidden")
        )

    @app.exception_handler(NotFoundError)
    async def _not_found(request: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content=error_body(request, "NotFound", str(exc)))

    @app.exception_handler(ConflictError)
    async def _conflict(request: Request, exc: ConflictError) -> JSONResponse:
        return JSONResponse(status_code=409, content=error_body(request, "Conflict", str(exc)))

    @app.exception_handler(InvalidDecisionTransition)
    async def _transition(request: Request, exc: InvalidDecisionTransition) -> JSONResponse:
        return JSONResponse(status_code=409, content=error_body(request, "Conflict", str(exc)))

    @app.exception_handler(DomainError)
    async def _domain(request: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(
            status_code=422, content=error_body(request, "BusinessRuleViolation", str(exc))
        )

    @app.exception_handler(ValueError)
    async def _value(request: Request, exc: ValueError) -> JSONResponse:
        return JSONResponse(
            status_code=400, content=error_body(request, "ValidationError", str(exc))
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = _HTTP_CODE_NAMES.get(exc.status_code, "InternalError")
        return JSONResponse(
            status_code=exc.status_code, content=error_body(request, code, str(exc.detail))
        )
