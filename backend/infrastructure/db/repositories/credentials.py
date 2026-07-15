"""SQL credential store (ADR-0009): password hashes live on the users table."""

from __future__ import annotations

from sqlalchemy.orm import Session, sessionmaker

from infrastructure.db.engine import session_scope
from infrastructure.db.models import UserRow
from shared_kernel.exceptions import NotFoundError
from shared_kernel.identifiers import UserId


class SqlCredentialStore:
    """Implements the identity CredentialStore port."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._sessions = session_factory

    def set_password_hash(self, user_id: UserId, password_hash: str) -> None:
        with session_scope(self._sessions) as session:
            row = session.get(UserRow, user_id.value)
            if row is None:
                raise NotFoundError(f"user not found: {user_id}")
            row.password_hash = password_hash

    def get_password_hash(self, user_id: UserId) -> str | None:
        with session_scope(self._sessions) as session:
            row = session.get(UserRow, user_id.value)
            return None if row is None else row.password_hash
