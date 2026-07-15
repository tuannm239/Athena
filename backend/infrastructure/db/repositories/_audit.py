"""Audit-record writer shared by repositories (SPEC-07, Audit)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from infrastructure.db.models import AuditRow


def write_audit(
    session: Session,
    *,
    entity_type: str,
    entity_id: uuid.UUID,
    action: str,
    snapshot: dict[str, Any],
) -> None:
    session.add(
        AuditRow(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            snapshot=snapshot,
            created_at=datetime.now(timezone.utc),
        )
    )
