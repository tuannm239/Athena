"""SQLAlchemy implementation of UserRepository (SPEC-07, users table)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from identity.domain.repository import UserRepository
from identity.domain.user import Role, User
from infrastructure.db.engine import session_scope
from infrastructure.db.models import UserRow
from shared_kernel.identifiers import UserId


def _from_row(row: UserRow) -> User:
    return User(
        email=row.email,
        status=row.status,
        role=Role(row.role),
        created_at=row.created_at,
        id=UserId(row.id),
    )


class SqlUserRepository(UserRepository):
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._sessions = session_factory

    def save(self, user: User) -> None:
        with session_scope(self._sessions) as session:
            existing = session.get(UserRow, user.id.value)
            if existing is None:
                session.add(
                    UserRow(
                        id=user.id.value,
                        email=user.email,
                        status=user.status,
                        role=user.role.value,
                        created_at=user.created_at,
                    )
                )
            else:
                existing.email = user.email
                existing.status = user.status
                existing.role = user.role.value

    def get(self, user_id: UserId) -> User | None:
        with session_scope(self._sessions) as session:
            row = session.get(UserRow, user_id.value)
            return None if row is None else _from_row(row)

    def get_by_email(self, email: str) -> User | None:
        with session_scope(self._sessions) as session:
            row = session.scalar(select(UserRow).where(UserRow.email == email))
            return None if row is None else _from_row(row)
