"""Identity use cases (SPEC-08 §Authentication; ADR-0009; ADR-0019).

Security-relevant actions (registration, logins, refresh rotation,
API-key lifecycle) are recorded in the audit trail when an audit log
is wired; passwords and raw keys never appear in audit details.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timezone

from identity.application.ports import (
    ApiKeyRecord,
    ApiKeyStore,
    AuthenticationError,
    CredentialStore,
    PasswordHasher,
    SecurityAuditLog,
    TokenPair,
    TokenService,
)
from identity.domain.repository import UserRepository
from identity.domain.user import Role, User
from shared_kernel.exceptions import ConflictError, NotFoundError

_ACTIVE = "active"

API_KEY_PREFIX = "athena_"


def hash_api_key(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


class _NullAudit:
    def record(self, *, action: str, subject: str, detail: str = "") -> None:
        del action, subject, detail


class RegisterUser:
    """Create an active user with Argon2id-hashed credentials."""

    def __init__(
        self,
        users: UserRepository,
        credentials: CredentialStore,
        hasher: PasswordHasher,
        audit: SecurityAuditLog | None = None,
    ) -> None:
        self._users = users
        self._credentials = credentials
        self._hasher = hasher
        self._audit = audit or _NullAudit()

    def execute(self, email: str, password: str, role: Role = Role.ANALYST) -> User:
        if len(password) < 8:
            raise ValueError("password must be at least 8 characters")
        if self._users.get_by_email(email) is not None:
            raise ConflictError(f"email already registered: {email}")
        user = User(email=email, status=_ACTIVE, role=role)
        self._users.save(user)
        self._credentials.set_password_hash(user.id, self._hasher.hash(password))
        self._audit.record(action="user.registered", subject=str(user.id), detail=user.role.value)
        return user


class AuthenticateUser:
    """Verify credentials and issue an access/refresh token pair."""

    def __init__(
        self,
        users: UserRepository,
        credentials: CredentialStore,
        hasher: PasswordHasher,
        tokens: TokenService,
        audit: SecurityAuditLog | None = None,
        api_keys: ApiKeyStore | None = None,
    ) -> None:
        self._users = users
        self._credentials = credentials
        self._hasher = hasher
        self._tokens = tokens
        self._audit = audit or _NullAudit()
        self._api_keys = api_keys

    def login(self, email: str, password: str) -> TokenPair:
        user = self._users.get_by_email(email)
        if user is None or user.status != _ACTIVE:
            self._audit.record(action="auth.login.failure", subject=email, detail="unknown user")
            raise AuthenticationError("invalid credentials")
        stored = self._credentials.get_password_hash(user.id)
        if stored is None or not self._hasher.verify(password, stored):
            self._audit.record(
                action="auth.login.failure", subject=str(user.id), detail="bad password"
            )
            raise AuthenticationError("invalid credentials")
        self._audit.record(action="auth.login.success", subject=str(user.id))
        return self._tokens.issue(user.id)

    def refresh(self, refresh_token: str) -> TokenPair:
        try:
            user_id = self._tokens.verify_refresh(refresh_token)
        except AuthenticationError:
            self._audit.record(
                action="auth.refresh.rejected", subject="unknown", detail="invalid or reused"
            )
            raise
        user = self._users.get(user_id)
        if user is None or user.status != _ACTIVE:
            raise AuthenticationError("invalid refresh token")
        self._audit.record(action="auth.refresh.rotated", subject=str(user.id))
        return self._tokens.issue(user.id)

    def resolve_access_token(self, token: str) -> User:
        user = self._users.get(self._tokens.verify_access(token))
        if user is None or user.status != _ACTIVE:
            raise AuthenticationError("invalid access token")
        return user

    def resolve_api_key(self, raw_key: str) -> User:
        """X-API-Key authentication (ADR-0019); only the sha256 of the
        raw key is ever compared or stored."""
        if self._api_keys is None:
            raise AuthenticationError("API key authentication is not enabled")
        record = self._api_keys.find_by_hash(hash_api_key(raw_key))
        if record is None or record.revoked_at is not None:
            self._audit.record(action="auth.apikey.rejected", subject="unknown")
            raise AuthenticationError("invalid API key")
        user = self._users.get(record.user_id)
        if user is None or user.status != _ACTIVE:
            raise AuthenticationError("invalid API key")
        return user


class ApiKeyService:
    """API-key lifecycle: create (raw shown once), list, revoke."""

    def __init__(
        self,
        users: UserRepository,
        store: ApiKeyStore,
        audit: SecurityAuditLog | None = None,
    ) -> None:
        self._users = users
        self._store = store
        self._audit = audit or _NullAudit()

    def create(self, user: User, name: str) -> tuple[ApiKeyRecord, str]:
        if not name.strip():
            raise ValueError("api key requires a name")
        raw = API_KEY_PREFIX + secrets.token_urlsafe(32)
        record = ApiKeyRecord(
            id=uuid.uuid4(),
            user_id=user.id,
            name=name.strip(),
            prefix=raw[: len(API_KEY_PREFIX) + 6],
            created_at=datetime.now(timezone.utc),
        )
        self._store.add(record, hash_api_key(raw))
        self._audit.record(action="apikey.created", subject=str(user.id), detail=record.name)
        return record, raw

    def list_for(self, user: User) -> tuple[ApiKeyRecord, ...]:
        return self._store.list_for_user(user.id)

    def revoke(self, user: User, key_id: uuid.UUID) -> None:
        if not self._store.revoke(key_id, user.id):
            raise NotFoundError(f"api key not found: {key_id}")
        self._audit.record(action="apikey.revoked", subject=str(user.id), detail=str(key_id))
