"""SQL persistence for the company fundamentals read-model (per ticker JSON)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from infrastructure.db.engine import session_scope
from infrastructure.db.models import CompanyFundamentalsRow


class SqlCompanyFundamentalsRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._sessions = session_factory

    def upsert(self, ticker: str, payload: dict[str, Any]) -> None:
        key = ticker.upper()
        with session_scope(self._sessions) as session:
            row = session.get(CompanyFundamentalsRow, key)
            now = datetime.now(timezone.utc)
            if row is None:
                session.add(CompanyFundamentalsRow(ticker=key, payload=payload, updated_at=now))
            else:
                row.payload = payload
                row.updated_at = now

    def get(self, ticker: str) -> dict[str, Any] | None:
        with session_scope(self._sessions) as session:
            row = session.scalar(
                select(CompanyFundamentalsRow).where(
                    CompanyFundamentalsRow.ticker == ticker.upper()
                )
            )
            return None if row is None else dict(row.payload)
