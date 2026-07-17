"""Security adapters: Argon2id password hashing and JWT tokens (ADR-0009)."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher as _Argon2
from argon2.exceptions import VerifyMismatchError

from identity.application.ports import AuthenticationError, RefreshTokenStore, TokenPair
from infrastructure.config import Settings
from shared_kernel.identifiers import UserId

_ALGORITHM = "HS256"


class Argon2PasswordHasher:
    """Argon2id (argon2-cffi defaults) — implements the PasswordHasher port."""

    def __init__(self) -> None:
        self._hasher = _Argon2()

    def hash(self, password: str) -> str:
        return self._hasher.hash(password)

    def verify(self, password: str, hashed: str) -> bool:
        try:
            return self._hasher.verify(hashed, password)
        except VerifyMismatchError:
            return False


class JwtTokenService:
    """HS256 JWT access/refresh pairs — implements the TokenService port.

    With a `RefreshTokenStore` wired, refresh tokens are single-use
    (ADR-0019): issuing registers the jti, verification consumes it, and
    a second use of the same token is rejected (reuse detection).
    """

    def __init__(self, settings: Settings, refresh_store: RefreshTokenStore | None = None) -> None:
        self._settings = settings
        self._refresh_store = refresh_store

    def _encode(self, user_id: UserId, kind: str, ttl_seconds: int) -> tuple[str, str, datetime]:
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=ttl_seconds)
        jti = uuid.uuid4().hex
        payload = {"sub": str(user_id), "type": kind, "iat": now, "exp": expires_at, "jti": jti}
        return jwt.encode(payload, self._settings.jwt_secret, algorithm=_ALGORITHM), jti, expires_at

    def issue(self, user_id: UserId) -> TokenPair:
        access, _, _ = self._encode(user_id, "access", self._settings.access_token_ttl_seconds)
        refresh, jti, expires_at = self._encode(
            user_id, "refresh", self._settings.refresh_token_ttl_seconds
        )
        if self._refresh_store is not None:
            self._refresh_store.register(jti, user_id, expires_at)
        return TokenPair(access_token=access, refresh_token=refresh)

    def _verify(self, token: str, kind: str) -> dict[str, object]:
        try:
            payload: dict[str, object] = jwt.decode(
                token, self._settings.jwt_secret, algorithms=[_ALGORITHM]
            )
        except jwt.PyJWTError as exc:
            raise AuthenticationError("invalid token") from exc
        if payload.get("type") != kind:
            raise AuthenticationError("wrong token type")
        return payload

    def verify_access(self, token: str) -> UserId:
        return UserId.parse(str(self._verify(token, "access")["sub"]))

    def verify_refresh(self, token: str) -> UserId:
        payload = self._verify(token, "refresh")
        if self._refresh_store is not None:
            if not self._refresh_store.consume(str(payload.get("jti", ""))):
                raise AuthenticationError("refresh token already used or revoked")
        return UserId.parse(str(payload["sub"]))
