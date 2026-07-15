"""User entity — fields per SPEC-07 (Core Tables, users)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from shared_kernel.identifiers import UserId


@dataclass(frozen=True, slots=True)
class User:
    email: str
    status: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    id: UserId = field(default_factory=UserId)

    def __post_init__(self) -> None:
        if not self.email or "@" not in self.email:
            raise ValueError("user requires a valid email")
