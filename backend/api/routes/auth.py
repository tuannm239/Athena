"""Authentication endpoints (SPEC-08 §Authentication; ADR-0009)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request

from api.deps import Container, container, current_user
from api.envelope import ok
from api.schemas import (
    ApiKeyCreatedResponse,
    ApiKeyCreateRequest,
    ApiKeyResponse,
    Envelope,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from identity.domain.user import User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=201, summary="Register a new user")
async def register(
    request: Request, body: RegisterRequest, services: Container = Depends(container)
) -> Envelope[UserResponse]:
    user = services.register_user.execute(body.email, body.password)
    return ok(
        request,
        UserResponse(
            id=user.id.value,
            email=user.email,
            status=user.status,
            role=user.role.value,
            created_at=user.created_at,
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


@router.post("/api-keys", status_code=201, summary="Create an API key (raw key shown once)")
async def create_api_key(
    request: Request,
    body: ApiKeyCreateRequest,
    services: Container = Depends(container),
    user: User = Depends(current_user),
) -> Envelope[ApiKeyCreatedResponse]:
    record, raw = services.api_keys.create(user, body.name)
    return ok(
        request,
        ApiKeyCreatedResponse(
            id=record.id,
            name=record.name,
            prefix=record.prefix,
            created_at=record.created_at,
            api_key=raw,
        ),
    )


@router.get("/api-keys", summary="List the caller's API keys")
async def list_api_keys(
    request: Request,
    services: Container = Depends(container),
    user: User = Depends(current_user),
) -> Envelope[list[ApiKeyResponse]]:
    records = services.api_keys.list_for(user)
    return ok(
        request,
        [
            ApiKeyResponse(
                id=r.id,
                name=r.name,
                prefix=r.prefix,
                created_at=r.created_at,
                revoked_at=r.revoked_at,
            )
            for r in records
        ],
    )


@router.delete("/api-keys/{key_id}", status_code=200, summary="Revoke an API key")
async def revoke_api_key(
    request: Request,
    key_id: uuid.UUID,
    services: Container = Depends(container),
    user: User = Depends(current_user),
) -> Envelope[dict[str, str]]:
    services.api_keys.revoke(user, key_id)
    return ok(request, {"status": "revoked"})
