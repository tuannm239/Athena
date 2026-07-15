"""User repository interface.

SPEC-03 omits Identity from its repository list; the interface follows
the same pattern because SPEC-07 defines the `users` table and SPEC-08
authentication requires user persistence.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from identity.domain.user import User
from shared_kernel.identifiers import UserId


class UserRepository(ABC):
    @abstractmethod
    def save(self, user: User) -> None: ...

    @abstractmethod
    def get(self, user_id: UserId) -> User | None: ...

    @abstractmethod
    def get_by_email(self, email: str) -> User | None: ...
