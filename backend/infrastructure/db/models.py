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
    role: Mapped[str] = mapped_column(
        String(16), default="ANALYST", server_default="ANALYST"
    )  # ADR-0019
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
    direction: Mapped[str] = mapped_column(String(16))  # ADR-0006
    source: Mapped[str] = mapped_column(String(256))
    category: Mapped[str] = mapped_column(String(64))
    explanation: Mapped[str] = mapped_column(Text)
    reliability: Mapped[Decimal] = mapped_column(_SCORE)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(PortableJSON, default=dict)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class CompanyRow(Base):
    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = mapped_column(_UUID, primary_key=True)
    ticker: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(256))
    exchange: Mapped[str] = mapped_column(String(32))
    sector: Mapped[str] = mapped_column(String(128))
    industry: Mapped[str] = mapped_column(String(128))
    currency: Mapped[str] = mapped_column(String(3))
    status: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


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


class KgNodeRow(Base):
    __tablename__ = "kg_nodes"

    node_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    type: Mapped[str] = mapped_column(String(32), index=True)
    name: Mapped[str] = mapped_column(String(256))
    attributes: Mapped[dict[str, Any]] = mapped_column(PortableJSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class KgEdgeRow(Base):
    __tablename__ = "kg_edges"

    id: Mapped[uuid.UUID] = mapped_column(_UUID, primary_key=True, default=uuid.uuid4)
    source_id: Mapped[str] = mapped_column(String(200), ForeignKey("kg_nodes.node_id"), index=True)
    target_id: Mapped[str] = mapped_column(String(200), ForeignKey("kg_nodes.node_id"), index=True)
    relation: Mapped[str] = mapped_column(String(32))
    provenance: Mapped[str] = mapped_column(String(512))
    created_version: Mapped[int] = mapped_column(index=True)
    removed_version: Mapped[int | None] = mapped_column(index=True)


class JournalRow(Base):
    """Immutable decision journal entry (SPEC-12) — insert-only."""

    __tablename__ = "journal_entries"

    id: Mapped[uuid.UUID] = mapped_column(_UUID, primary_key=True, default=uuid.uuid4)
    decision_id: Mapped[uuid.UUID] = mapped_column(_UUID, index=True)
    original_hypothesis: Mapped[str] = mapped_column(Text)
    supporting_evidence: Mapped[list[str]] = mapped_column(PortableJSON, default=list)
    counter_evidence: Mapped[list[str]] = mapped_column(PortableJSON, default=list)
    expected_outcome: Mapped[str] = mapped_column(Text)
    actual_outcome: Mapped[str] = mapped_column(Text, default="")
    lessons_learned: Mapped[str] = mapped_column(Text, default="")
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class AuditRow(Base):
    """Immutable audit record (SPEC-07, Audit).

    Rows are insert-only; no repository exposes an update or delete path.
    """

    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(_UUID, primary_key=True, default=uuid.uuid4)
    entity_type: Mapped[str] = mapped_column(String(64), index=True)
    entity_id: Mapped[uuid.UUID] = mapped_column(_UUID, index=True)
    action: Mapped[str] = mapped_column(String(64))  # CREATE | UPDATE | security events
    snapshot: Mapped[dict[str, Any]] = mapped_column(PortableJSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class ApiKeyRow(Base):
    """API keys (ADR-0019): only the sha256 of the raw key is stored."""

    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(_UUID, primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(_UUID, ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(128))
    prefix: Mapped[str] = mapped_column(String(16))
    key_hash: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)


class RefreshTokenRow(Base):
    """Single-use refresh tokens (ADR-0019 rotation / reuse detection)."""

    __tablename__ = "refresh_tokens"

    jti: Mapped[str] = mapped_column(String(32), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(_UUID, ForeignKey("users.id"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
