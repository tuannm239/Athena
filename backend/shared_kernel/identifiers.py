"""Typed identifiers for the shared kernel.

Domain rule: identifiers are opaque, immutable, and comparable only
within their own type (a SnapshotId is never equal to a RunId).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Self


@dataclass(frozen=True, slots=True)
class _Id:
    value: uuid.UUID = field(default_factory=uuid.uuid4)

    @classmethod
    def parse(cls, raw: str) -> Self:
        return cls(uuid.UUID(raw))

    def __str__(self) -> str:
        return str(self.value)

    def __eq__(self, other: object) -> bool:
        # Identity equality is type-strict: different Id subclasses never compare equal.
        return type(other) is type(self) and other.value == self.value

    def __hash__(self) -> int:
        return hash((type(self).__name__, self.value))


@dataclass(frozen=True, slots=True, eq=False)
class SnapshotId(_Id): ...


@dataclass(frozen=True, slots=True, eq=False)
class RunId(_Id): ...


@dataclass(frozen=True, slots=True, eq=False)
class InstrumentId(_Id): ...


@dataclass(frozen=True, slots=True, eq=False)
class DecisionId(_Id): ...


@dataclass(frozen=True, slots=True, eq=False)
class ExplanationId(_Id): ...


@dataclass(frozen=True, slots=True, eq=False)
class EvidenceId(_Id): ...


@dataclass(frozen=True, slots=True, eq=False)
class PortfolioId(_Id): ...


@dataclass(frozen=True, slots=True, eq=False)
class CompanyId(_Id): ...


@dataclass(frozen=True, slots=True, eq=False)
class UserId(_Id): ...
