"""Company entity (SPEC-03, Entities)."""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from shared_kernel.identifiers import CompanyId


@dataclass(frozen=True, slots=True)
class Company:
    ticker: str
    exchange: str
    industry: str
    sector: str
    quality_score: Decimal | None = None
    valuation_score: Decimal | None = None
    growth_score: Decimal | None = None
    id: CompanyId = field(default_factory=CompanyId)

    def __post_init__(self) -> None:
        if not self.ticker:
            raise ValueError("company ticker must not be empty")
