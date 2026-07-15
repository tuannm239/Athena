"""Authentication endpoints (SPEC-08 §Authentication; ADR-0009)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from api.deps import Container, container
from api.envelope import ok
from api.schemas import (
    Envelope,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=201, summary="Register a new user")
async def register(
    request: Request, body: RegisterRequest, services: Container = Depends(container)
) -> Envelope[UserResponse]:
    user = services.register_user.execute(body.email, body.password)
    return ok(
        request,
        UserResponse(
            id=user.id.value, email=user.email, status=user.status, created_at=user.created_at
        ),
    )


@router.post("/login", summary="Exchange credentials for a token pair")
async def login(
    request: Request, body: LoginRequest, services: Container = Depends(container)
) -> Envelope[TokenResponse]:
    pair = services.authenticate.login(body.email, body.password)
    return ok(
        request,
        TokenResponse(
            access_token=pair.access_token,
            refresh_token=pair.refresh_token,
            token_type=pair.token_type,
        ),
    )


@router.post("/refresh", summary="Rotate the token pair")
async def refresh(
    request: Request, body: RefreshRequest, services: Container = Depends(container)
) -> Envelope[TokenResponse]:
    pair = services.authenticate.refresh(body.refresh_token)
    return ok(
        request,
        TokenResponse(
            access_token=pair.access_token,
            refresh_token=pair.refresh_token,
            token_type=pair.token_type,
        ),
    )
