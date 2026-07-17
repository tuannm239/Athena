"""User entity — fields per SPEC-07 (Core Tables, users); RBAC per ADR-0019."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum

from shared_kernel.identifiers import UserId


class Role(StrEnum):
    """RBAC roles (ADR-0019): VIEWER reads; ANALYST also writes
    decisions and portfolios; ADMIN additionally administers."""

    VIEWER = "VIEWER"
    ANALYST = "ANALYST"
    ADMIN = "ADMIN"


@dataclass(frozen=True, slots=True)
class User:
    email: str
    status: str
    role: Role = Role.ANALYST
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    id: UserId = field(default_factory=UserId)

    def __post_init__(self) -> None:
        if not self.email or "@" not in self.email:
            raise ValueError("user requires a valid email")
