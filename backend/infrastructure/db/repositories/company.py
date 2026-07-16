"""SQL implementation of CompanyRepository (companies table, Executive Directive)."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from company.domain.company import Company
from company.domain.repository import CompanyRepository
from infrastructure.db.engine import session_scope
from infrastructure.db.models import CompanyRow
from shared_kernel.identifiers import CompanyId
from shared_kernel.money import Currency


def _from_row(row: CompanyRow) -> Company:
    return Company(
        ticker=row.ticker,
        name=row.name,
        exchange=row.exchange,
        sector=row.sector,
        industry=row.industry,
        currency=Currency(row.currency),
        status=row.status,
        created_at=row.created_at,
        id=CompanyId(row.id),
    )


class SqlCompanyRepository(CompanyRepository):
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._sessions = session_factory

    def save(self, company: Company) -> None:
        with session_scope(self._sessions) as session:
            row = session.scalar(select(CompanyRow).where(CompanyRow.ticker == company.ticker))
            now = datetime.now(timezone.utc)
            if row is None:
                session.add(
                    CompanyRow(
                        id=company.id.value,
                        ticker=company.ticker,
                        name=company.name,
                        exchange=company.exchange,
                        sector=company.sector,
                        industry=company.industry,
                        currency=company.currency.value,
                        status=company.status,
                        created_at=company.created_at,
                        updated_at=now,
                    )
                )
                return
            row.name = company.name
            row.exchange = company.exchange
            row.sector = company.sector
            row.industry = company.industry
            row.currency = company.currency.value
            row.status = company.status
            row.updated_at = now

    def get_by_ticker(self, ticker: str) -> Company | None:
        with session_scope(self._sessions) as session:
            row = session.scalar(select(CompanyRow).where(CompanyRow.ticker == ticker))
            return None if row is None else _from_row(row)
