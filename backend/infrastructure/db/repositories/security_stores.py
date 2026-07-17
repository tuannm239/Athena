"""Security stores (ADR-0019): API keys, single-use refresh tokens,
and the security audit log over the SPEC-07 audit trail."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from identity.application.ports import ApiKeyRecord
from infrastructure.db.engine import session_scope
from infrastructure.db.models import ApiKeyRow, RefreshTokenRow
from infrastructure.db.repositories._audit import write_audit
from shared_kernel.identifiers import UserId


def _record(row: ApiKeyRow) -> ApiKeyRecord:
    return ApiKeyRecord(
        id=row.id,
        user_id=UserId(row.user_id),
        name=row.name,
        prefix=row.prefix,
        created_at=row.created_at,
        revoked_at=row.revoked_at,
    )


class SqlApiKeyStore:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._sessions = session_factory

    def add(self, record: ApiKeyRecord, key_hash: str) -> None:
        with session_scope(self._sessions) as session:
            session.add(
                ApiKeyRow(
                    id=record.id,
                    user_id=record.user_id.value,
                    name=record.name,
                    prefix=record.prefix,
                    key_hash=key_hash,
                    created_at=record.created_at,
                    revoked_at=record.revoked_at,
                )
            )

    def find_by_hash(self, key_hash: str) -> ApiKeyRecord | None:
        with session_scope(self._sessions) as session:
            row = session.scalar(select(ApiKeyRow).where(ApiKeyRow.key_hash == key_hash))
            return None if row is None else _record(row)

    def list_for_user(self, user_id: UserId) -> tuple[ApiKeyRecord, ...]:
        with session_scope(self._sessions) as session:
            rows = session.scalars(
                select(ApiKeyRow)
                .where(ApiKeyRow.user_id == user_id.value)
                .order_by(ApiKeyRow.created_at)
            ).all()
            return tuple(_record(row) for row in rows)

    def revoke(self, key_id: uuid.UUID, user_id: UserId) -> bool:
        with session_scope(self._sessions) as session:
            row = session.get(ApiKeyRow, key_id)
            if row is None or row.user_id != user_id.value or row.revoked_at is not None:
                return False
            row.revoked_at = datetime.now(timezone.utc)
            return True


class SqlRefreshTokenStore:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._sessions = session_factory

    def register(self, jti: str, user_id: UserId, expires_at: datetime) -> None:
        with session_scope(self._sessions) as session:
            session.add(RefreshTokenRow(jti=jti, user_id=user_id.value, expires_at=expires_at))

    def consume(self, jti: str) -> bool:
        with session_scope(self._sessions) as session:
            row = session.get(RefreshTokenRow, jti)
            if row is None or row.revoked_at is not None:
                return False
            expires_at = row.expires_at
            if expires_at.tzinfo is None:  # SQLite returns naive datetimes
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if expires_at < datetime.now(timezone.utc):
                return False
            row.revoked_at = datetime.now(timezone.utc)
            return True


class SqlSecurityAuditLog:
    """Security events in the SPEC-07 audit trail (insert-only)."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._sessions = session_factory

    def record(self, *, action: str, subject: str, detail: str = "") -> None:
        try:
            entity_id = uuid.UUID(subject)
        except ValueError:
            entity_id = uuid.uuid5(uuid.NAMESPACE_URL, subject)
        with session_scope(self._sessions) as session:
            write_audit(
                session,
                entity_type="security",
                entity_id=entity_id,
                action=action,
                snapshot={"subject": subject, "detail": detail},
            )
