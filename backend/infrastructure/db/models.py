"""ORM models for the PostgreSQL system of record (SPEC-07, Core Tables).

Design principles applied (SPEC-07): UUID primary keys, UTC timestamps,
indexes on ticker/portfolio_id/decision_id/created_at/factor_id, and an
immutable audit table. Business rules live in the domain layer only —
these classes store state.

Columns beyond the SPEC-07 minimum exist solely so the SPEC-03/04 domain
aggregates round-trip losslessly (ADR-0005 §2).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.db.base import Base, PortableJSON

_UUID = Uuid(as_uuid=True)
_MONEY = Numeric(24, 6)
_SCORE = Numeric(12, 9)


class UserRow(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(_UUID, primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True)
    status: Mapped[str] = mapped_column(String(32))
    password_hash: Mapped[str | None] = mapped_column(String(256))  # ADR-0009
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class PortfolioRow(Base):
    __tablename__ = "portfolios"

    id: Mapped[uuid.UUID] = mapped_column(_UUID, primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(_UUID, ForeignKey("users.id"), index=True)
    base_currency: Mapped[str] = mapped_column(String(3))
    cash_amount: Mapped[Decimal] = mapped_column(_MONEY)
    constraints: Mapped[dict[str, Any]] = mapped_column(PortableJSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    positions: Mapped[list[PositionRow]] = relationship(
        cascade="all, delete-orphan", lazy="selectin"
    )


class PositionRow(Base):
    __tablename__ = "positions"

    id: Mapped[uuid.UUID] = mapped_column(_UUID, primary_key=True, default=uuid.uuid4)
    portfolio_id: Mapped[uuid.UUID] = mapped_column(_UUID, ForeignKey("portfolios.id"), index=True)
    ticker: Mapped[str] = mapped_column(String(32), index=True)
    quantity: Mapped[Decimal] = mapped_column(_MONEY)
    average_cost: Mapped[Decimal] = mapped_column(_MONEY)
    market_value: Mapped[Decimal] = mapped_column(_MONEY)
    unrealized_pnl: Mapped[Decimal] = mapped_column(_MONEY)
    currency: Mapped[str] = mapped_column(String(3))


class DecisionRow(Base):
    __tablename__ = "decisions"

    id: Mapped[uuid.UUID] = mapped_column(_UUID, primary_key=True)
    hypothesis: Mapped[str] = mapped_column(Text)
    probability: Mapped[Decimal] = mapped_column(_SCORE)
    confidence: Mapped[Decimal] = mapped_column(_SCORE)
    status: Mapped[str] = mapped_column(String(32), index=True)
    decision_type: Mapped[str | None] = mapped_column(String(32))
    expected_return: Mapped[Decimal | None] = mapped_column(_SCORE)
    expected_drawdown: Mapped[Decimal | None] = mapped_column(_SCORE)
    expected_utility: Mapped[Decimal | None] = mapped_column(_SCORE)
    position_size: Mapped[Decimal | None] = mapped_column(_SCORE)
    portfolio_impact: Mapped[str | None] = mapped_column(Text)
    explanation: Mapped[str | None] = mapped_column(Text)
    assumptions: Mapped[list[str]] = mapped_column(PortableJSON, default=list)
    invalidation_conditions: Mapped[list[str]] = mapped_column(PortableJSON, default=list)
    risk_assessment: Mapped[dict[str, Any] | None] = mapped_column(PortableJSON)
    review_history: Mapped[list[dict[str, Any]]] = mapped_column(PortableJSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    evidence: Mapped[list[EvidenceRow]] = relationship(
        cascade="all, delete-orphan", lazy="selectin"
    )


class EvidenceRow(Base):
    __tablename__ = "evidence"

    id: Mapped[uuid.UUID] = mapped_column(_UUID, primary_key=True)
    decision_id: Mapped[uuid.UUID] = mapped_column(_UUID, ForeignKey("decisions.id"), index=True)
    kind: Mapped[str] = mapped_column(String(16))  # SUPPORTING | COUNTER (SPEC-03/04)
    source: Mapped[str] = mapped_column(String(256))
    category: Mapped[str] = mapped_column(String(64))
    description: Mapped[str] = mapped_column(Text)
    confidence: Mapped[Decimal] = mapped_column(_SCORE)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class FactorRow(Base):
    __tablename__ = "factors"

    id: Mapped[uuid.UUID] = mapped_column(_UUID, primary_key=True, default=uuid.uuid4)
    factor_id: Mapped[str] = mapped_column(String(128), index=True)
    version: Mapped[str] = mapped_column(String(32))
    category: Mapped[str] = mapped_column(String(64))
    value: Mapped[Decimal] = mapped_column(_MONEY)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    __table_args__ = (Index("ix_factors_factor_id_version", "factor_id", "version"),)


class FeatureDefinitionRow(Base):
    __tablename__ = "feature_definitions"

    id: Mapped[uuid.UUID] = mapped_column(_UUID, primary_key=True, default=uuid.uuid4)
    feature_id: Mapped[str] = mapped_column(String(128), index=True)
    version: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(16), index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(PortableJSON)
    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    __table_args__ = (
        Index("uq_feature_definitions_id_version", "feature_id", "version", unique=True),
    )


class DatasetRow(Base):
    __tablename__ = "datasets"

    id: Mapped[uuid.UUID] = mapped_column(_UUID, primary_key=True, default=uuid.uuid4)
    dataset_id: Mapped[str] = mapped_column(String(128), index=True)
    version: Mapped[str] = mapped_column(String(64))
    snapshot_id: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(16), index=True)
    lineage: Mapped[dict[str, Any]] = mapped_column(PortableJSON)
    quality: Mapped[dict[str, Any]] = mapped_column(PortableJSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    __table_args__ = (Index("uq_datasets_id_version", "dataset_id", "version", unique=True),)


class AuditRow(Base):
    """Immutable audit record (SPEC-07, Audit).

    Rows are insert-only; no repository exposes an update or delete path.
    """

    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(_UUID, primary_key=True, default=uuid.uuid4)
    entity_type: Mapped[str] = mapped_column(String(64), index=True)
    entity_id: Mapped[uuid.UUID] = mapped_column(_UUID, index=True)
    action: Mapped[str] = mapped_column(String(16))  # CREATE | UPDATE
    snapshot: Mapped[dict[str, Any]] = mapped_column(PortableJSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
