"""Company entity (SPEC-03 Entities; companies table per Executive Directive)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal

from shared_kernel.identifiers import CompanyId
from shared_kernel.money import Currency


@dataclass(frozen=True, slots=True)
class Company:
    ticker: str
    name: str
    exchange: str
    sector: str
    industry: str
    currency: Currency
    status: str = "active"
    quality_score: Decimal | None = None
    valuation_score: Decimal | None = None
    growth_score: Decimal | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    id: CompanyId = field(default_factory=CompanyId)

    def __post_init__(self) -> None:
        if not self.ticker:
            raise ValueError("company ticker must not be empty")
        if not self.name:
            raise ValueError("company name must not be empty")
