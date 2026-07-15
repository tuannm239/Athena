"""Identity ports (hexagonal): hashing, credential storage, token service.

Credentials are infrastructure state (ADR-0009); the domain User entity
never carries them.
"""

from __future__ import annotations

from dataclasses import dataclass
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
