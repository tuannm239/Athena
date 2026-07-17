"""Identity ports (hexagonal): hashing, credential storage, token service.

Credentials are infrastructure state (ADR-0009); the domain User entity
never carries them.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from shared_kernel.identifiers import UserId


class PasswordHasher(Protocol):
    def hash(self, password: str) -> str: ...

    def verify(self, password: str, hashed: str) -> bool: ...


class CredentialStore(Protocol):
    def set_password_hash(self, user_id: UserId, password_hash: str) -> None: ...

    def get_password_hash(self, user_id: UserId) -> str | None: ...


@dataclass(frozen=True, slots=True)
class TokenPair:
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenService(Protocol):
    def issue(self, user_id: UserId) -> TokenPair: ...

    def verify_access(self, token: str) -> UserId:
        """Return the subject or raise AuthenticationError."""
        ...

    def verify_refresh(self, token: str) -> UserId: ...


class AuthenticationError(Exception):
    """Invalid credentials or token (mapped to HTTP 401, SPEC-08)."""


class AuthorizationError(Exception):
    """Authenticated but not allowed (mapped to HTTP 403, SPEC-08)."""


class RefreshTokenStore(Protocol):
    """Single-use refresh tokens (ADR-0019 rotation with reuse detection)."""

    def register(self, jti: str, user_id: UserId, expires_at: datetime) -> None: ...

    def consume(self, jti: str) -> bool:
        """Atomically revoke; False if unknown, already used or expired."""
        ...


@dataclass(frozen=True, slots=True)
class ApiKeyRecord:
    """API key metadata; the raw key is shown once and never stored."""

    id: uuid.UUID
    user_id: UserId
    name: str
    prefix: str
    created_at: datetime
    revoked_at: datetime | None = None


class ApiKeyStore(Protocol):
    def add(self, record: ApiKeyRecord, key_hash: str) -> None: ...

    def find_by_hash(self, key_hash: str) -> ApiKeyRecord | None: ...

    def list_for_user(self, user_id: UserId) -> tuple[ApiKeyRecord, ...]: ...

    def revoke(self, key_id: uuid.UUID, user_id: UserId) -> bool:
        """Revoke the user's key; False when it isn't theirs or is unknown."""
        ...


class SecurityAuditLog(Protocol):
    """Security-relevant events land in the SPEC-07 audit trail."""

    def record(self, *, action: str, subject: str, detail: str = "") -> None: ...
