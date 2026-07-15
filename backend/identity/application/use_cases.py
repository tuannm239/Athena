"""Identity use cases (SPEC-08 §Authentication; ADR-0009)."""

from __future__ import annotations

from identity.application.ports import (
    AuthenticationError,
    CredentialStore,
    PasswordHasher,
    TokenPair,
    TokenService,
)
from identity.domain.repository import UserRepository
from identity.domain.user import User
from shared_kernel.exceptions import ConflictError

_ACTIVE = "active"


class RegisterUser:
    """Create an active user with Argon2id-hashed credentials."""

    def __init__(
        self, users: UserRepository, credentials: CredentialStore, hasher: PasswordHasher
    ) -> None:
        self._users = users
        self._credentials = credentials
        self._hasher = hasher

    def execute(self, email: str, password: str) -> User:
        if len(password) < 8:
            raise ValueError("password must be at least 8 characters")
        if self._users.get_by_email(email) is not None:
            raise ConflictError(f"email already registered: {email}")
        user = User(email=email, status=_ACTIVE)
        self._users.save(user)
        self._credentials.set_password_hash(user.id, self._hasher.hash(password))
        return user


class AuthenticateUser:
    """Verify credentials and issue an access/refresh token pair."""

    def __init__(
        self,
        users: UserRepository,
        credentials: CredentialStore,
        hasher: PasswordHasher,
        tokens: TokenService,
    ) -> None:
        self._users = users
        self._credentials = credentials
        self._hasher = hasher
        self._tokens = tokens

    def login(self, email: str, password: str) -> TokenPair:
        user = self._users.get_by_email(email)
        if user is None or user.status != _ACTIVE:
            raise AuthenticationError("invalid credentials")
        stored = self._credentials.get_password_hash(user.id)
        if stored is None or not self._hasher.verify(password, stored):
            raise AuthenticationError("invalid credentials")
        return self._tokens.issue(user.id)

    def refresh(self, refresh_token: str) -> TokenPair:
        user_id = self._tokens.verify_refresh(refresh_token)
        user = self._users.get(user_id)
        if user is None or user.status != _ACTIVE:
            raise AuthenticationError("invalid refresh token")
        return self._tokens.issue(user.id)

    def resolve_access_token(self, token: str) -> User:
        user = self._users.get(self._tokens.verify_access(token))
        if user is None or user.status != _ACTIVE:
            raise AuthenticationError("invalid access token")
        return user
