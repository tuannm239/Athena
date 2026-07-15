"""SQLAlchemy implementation of PortfolioRepository (SPEC-03, SPEC-07)."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from infrastructure.db.engine import session_scope
from infrastructure.db.models import PortfolioRow, PositionRow
from infrastructure.db.repositories._audit import write_audit
from portfolio.domain.constraints import PortfolioConstraints
from portfolio.domain.portfolio import Portfolio
from portfolio.domain.position import Position
from portfolio.domain.repository import PortfolioRepository
from shared_kernel.identifiers import PortfolioId, UserId
from shared_kernel.measures import Percentage
from shared_kernel.money import Currency, Money


def _constraints_to_json(constraints: PortfolioConstraints) -> dict[str, Any]:
    def pct(value: Percentage | None) -> str | None:
        return None if value is None else str(value.value)

    return {
        "max_position_weight": pct(constraints.max_position_weight),
        "max_sector_exposure": pct(constraints.max_sector_exposure),
        "min_cash_reserve": pct(constraints.min_cash_reserve),
        "liquidity_threshold": (
            None
            if constraints.liquidity_threshold is None
            else str(constraints.liquidity_threshold)
        ),
        "risk_budget": None if constraints.risk_budget is None else str(constraints.risk_budget),
        "max_turnover": pct(constraints.max_turnover),
    }


def _constraints_from_json(payload: dict[str, Any]) -> PortfolioConstraints:
    def pct(key: str) -> Percentage | None:
        raw = payload.get(key)
        return None if raw is None else Percentage(Decimal(raw))

    def dec(key: str) -> Decimal | None:
        raw = payload.get(key)
        return None if raw is None else Decimal(raw)

    return PortfolioConstraints(
        max_position_weight=pct("max_position_weight"),
        max_sector_exposure=pct("max_sector_exposure"),
        min_cash_reserve=pct("min_cash_reserve"),
        liquidity_threshold=dec("liquidity_threshold"),
        risk_budget=dec("risk_budget"),
        max_turnover=pct("max_turnover"),
    )


def _position_rows(portfolio: Portfolio) -> list[PositionRow]:
    return [
        PositionRow(
            portfolio_id=portfolio.id.value,
            ticker=p.ticker,
            quantity=p.quantity,
            average_cost=p.average_cost.amount,
            market_value=p.market_value.amount,
            unrealized_pnl=p.unrealized_pnl.amount,
            currency=p.market_value.currency.value,
        )
        for p in portfolio.positions
    ]


def _from_row(row: PortfolioRow) -> Portfolio:
    return Portfolio(
        owner_id=UserId(row.user_id),
        cash_balance=Money(Decimal(row.cash_amount), Currency(row.base_currency)),
        positions=tuple(_position_from_row(p) for p in row.positions),
        constraints=_constraints_from_json(row.constraints),
        id=PortfolioId(row.id),
    )


def _position_from_row(row: PositionRow) -> Position:
    currency = Currency(row.currency)
    return Position(
        ticker=row.ticker,
        quantity=Decimal(row.quantity),
        average_cost=Money(Decimal(row.average_cost), currency),
        market_value=Money(Decimal(row.market_value), currency),
        unrealized_pnl=Money(Decimal(row.unrealized_pnl), currency),
    )


class SqlPortfolioRepository(PortfolioRepository):
    """Persists the Portfolio aggregate; every save writes an audit record."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._sessions = session_factory

    def save(self, portfolio: Portfolio) -> None:
        with session_scope(self._sessions) as session:
            existing = session.get(PortfolioRow, portfolio.id.value)
            action = "UPDATE" if existing is not None else "CREATE"
            if existing is not None:
                created_at = existing.created_at
                session.delete(existing)
                session.flush()
            else:
                created_at = datetime.now(timezone.utc)
            session.add(
                PortfolioRow(
                    id=portfolio.id.value,
                    user_id=portfolio.owner_id.value,
                    base_currency=portfolio.cash_balance.currency.value,
                    cash_amount=portfolio.cash_balance.amount,
                    constraints=_constraints_to_json(portfolio.constraints),
                    created_at=created_at,
                    positions=_position_rows(portfolio),
                )
            )
            write_audit(
                session,
                entity_type="portfolio",
                entity_id=portfolio.id.value,
                action=action,
                snapshot={
                    "cash": str(portfolio.cash_balance.amount),
                    "currency": portfolio.cash_balance.currency.value,
                    "positions": [p.ticker for p in portfolio.positions],
                },
            )

    def get(self, portfolio_id: PortfolioId) -> Portfolio | None:
        with session_scope(self._sessions) as session:
            row = session.get(PortfolioRow, portfolio_id.value)
            return None if row is None else _from_row(row)

    def list_by_owner(self, owner_id: UserId, *, limit: int, offset: int) -> tuple[Portfolio, ...]:
        with session_scope(self._sessions) as session:
            rows = session.scalars(
                select(PortfolioRow)
                .where(PortfolioRow.user_id == owner_id.value)
                .order_by(PortfolioRow.created_at.desc())
                .limit(limit)
                .offset(offset)
            ).all()
            return tuple(_from_row(r) for r in rows)

    def count_by_owner(self, owner_id: UserId) -> int:
        with session_scope(self._sessions) as session:
            return int(
                session.scalar(
                    select(func.count())
                    .select_from(PortfolioRow)
                    .where(PortfolioRow.user_id == owner_id.value)
                )
                or 0
            )
