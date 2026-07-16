"""Probability value objects.

Domain rules:
- Probability is a Decimal in [0, 1].
- A ProbabilityDistribution's masses sum to 1 (within tolerance).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from types import MappingProxyType
from typing import Mapping

_TOL = Decimal("0.000001")


@dataclass(frozen=True, slots=True)
class Probability:
    value: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.value, Decimal):
            raise TypeError("Probability.value must be Decimal")
        if not (Decimal(0) <= self.value <= Decimal(1)):
            raise ValueError(f"Probability out of range: {self.value}")

    @property
    def complement(self) -> "Probability":
        return Probability(Decimal(1) - self.value)


@dataclass(frozen=True, slots=True)
class Confidence:
    """Reliability of the current evaluation, in [0, 1] (SPEC-03)."""

    value: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.value, Decimal):
            raise TypeError("Confidence.value must be Decimal")
        if not (Decimal(0) <= self.value <= Decimal(1)):
            raise ValueError(f"Confidence out of range: {self.value}")


@dataclass(frozen=True, slots=True)
class Reliability:
    """Trustworthiness of a single evidence item, in [0, 1] (ADR-0006)."""

    value: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.value, Decimal):
            raise TypeError("Reliability.value must be Decimal")
        if not (Decimal(0) <= self.value <= Decimal(1)):
            raise ValueError(f"Reliability out of range: {self.value}")


class DistributionError(ValueError):
    """Raised when masses do not form a valid distribution."""


@dataclass(frozen=True)
class ProbabilityDistribution:
    """Discrete distribution over string-labelled outcomes."""

    masses: Mapping[str, Probability]

    def __post_init__(self) -> None:
        if not self.masses:
            raise DistributionError("distribution must not be empty")
        total = sum(p.value for p in self.masses.values())
        if abs(total - Decimal(1)) > _TOL:
            raise DistributionError(f"masses must sum to 1, got {total}")
        object.__setattr__(self, "masses", MappingProxyType(dict(self.masses)))

    def mode(self) -> str:
        return max(self.masses, key=lambda k: self.masses[k].value)

    def p(self, label: str) -> Probability:
        return self.masses[label]
