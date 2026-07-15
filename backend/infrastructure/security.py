"""Security adapters: Argon2id password hashing and JWT tokens (ADR-0009)."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher as _Argon2
from argon2.exceptions import VerifyMismatchError

from identity.application.ports import AuthenticationError, TokenPair
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
    """HS256 JWT access/refresh pairs — implements the TokenService port."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def _encode(self, user_id: UserId, kind: str, ttl_seconds: int) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(user_id),
            "type": kind,
            "iat": now,
            "exp": now + timedelta(seconds=ttl_seconds),
            "jti": uuid.uuid4().hex,
        }
        return jwt.encode(payload, self._settings.jwt_secret, algorithm=_ALGORITHM)

    def issue(self, user_id: UserId) -> TokenPair:
        return TokenPair(
            access_token=self._encode(user_id, "access", self._settings.access_token_ttl_seconds),
            refresh_token=self._encode(
                user_id, "refresh", self._settings.refresh_token_ttl_seconds
            ),
        )

    def _verify(self, token: str, kind: str) -> UserId:
        try:
            payload = jwt.decode(token, self._settings.jwt_secret, algorithms=[_ALGORITHM])
        except jwt.PyJWTError as exc:
            raise AuthenticationError("invalid token") from exc
        if payload.get("type") != kind:
            raise AuthenticationError("wrong token type")
        return UserId.parse(str(payload["sub"]))

    def verify_access(self, token: str) -> UserId:
        return self._verify(token, "access")

    def verify_refresh(self, token: str) -> UserId:
        return self._verify(token, "refresh")
