"""Company repository interface (SPEC-03, Repository Interfaces)."""

from __future__ import annotations

from abc import ABC, abstractmethod

from company.domain.company import Company


class CompanyRepository(ABC):
    @abstractmethod
    def save(self, company: Company) -> None: ...

    @abstractmethod
    def get_by_ticker(self, ticker: str) -> Company | None: ...
