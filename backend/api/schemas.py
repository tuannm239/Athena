"""Pydantic models at the API boundary (SPEC-02 §API; SPEC-08).

Domain objects are never serialized directly; every response is wrapped
in the standard envelope (SPEC-08 §Standard Response). Decimals are
serialized as JSON strings by pydantic v2, preserving exactness.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from decision_kernel.domain.decision import DecisionStatus, DecisionType
from decision_kernel.domain.evidence import EvidenceDirection
from market.domain.market_context import Regime
from risk.domain.risk_assessment import RiskLevel
from shared_kernel.money import Currency

T = TypeVar("T")


class ApiError(BaseModel):
    code: str
    detail: str


class Envelope(BaseModel, Generic[T]):
    """SPEC-08 §Standard Response: request_id, timestamp, status, data, errors."""

    request_id: str
    timestamp: datetime
    status: Literal["ok", "error"]
    data: T | None = None
    errors: list[ApiError] | None = None


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int


# -- auth ---------------------------------------------------------------------


class RegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    status: str
    role: str
    created_at: datetime


class ApiKeyCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=128)


class ApiKeyResponse(BaseModel):
    id: uuid.UUID
    name: str
    prefix: str
    created_at: datetime
    revoked_at: datetime | None = None


class ApiKeyCreatedResponse(BaseModel):
    id: uuid.UUID
    name: str
    prefix: str
    created_at: datetime
    api_key: str  # shown exactly once; only its hash is stored (ADR-0019)


# -- decisions ----------------------------------------------------------------


class EvidenceIn(BaseModel):
    """ADR-0006 evidence: direction is explicit, never inferred."""

    source: str = Field(min_length=1, max_length=256)
    category: str = Field(min_length=1, max_length=64)
    explanation: str = Field(min_length=1)
    reliability: Decimal = Field(ge=0, le=1)
    direction: EvidenceDirection
    metadata: dict[str, str] = Field(default_factory=dict)


class EvidenceOut(EvidenceIn):
    id: uuid.UUID
    timestamp: datetime


class RiskAssessmentModel(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    var: Decimal
    cvar: Decimal
    max_drawdown: Decimal
    stress_score: Decimal
    liquidity_score: Decimal
    level: RiskLevel
    confidence: Decimal = Field(ge=0, le=1)


class ReviewRecordOut(BaseModel):
    outcome: DecisionStatus
    at: datetime
    note: str


class DecisionCreateRequest(BaseModel):
    hypothesis: str = Field(min_length=1)
    probability: Decimal = Field(ge=0, le=1)
    confidence: Decimal = Field(ge=0, le=1)
    decision_type: DecisionType | None = None
    expected_return: Decimal | None = None
    expected_drawdown: Decimal | None = None
    assumptions: list[str] = Field(default_factory=list)
    invalidation_conditions: list[str] = Field(default_factory=list)
    evidence: list[EvidenceIn] = Field(default_factory=list)


class DecisionUpdateRequest(BaseModel):
    """PATCH semantics: omitted fields stay unchanged (SPEC-08)."""

    explanation: str | None = None
    assumptions: list[str] | None = None
    invalidation_conditions: list[str] | None = None
    add_evidence: list[EvidenceIn] = Field(default_factory=list)
    risk_assessment: RiskAssessmentModel | None = None
    status: DecisionStatus | None = None
    review_note: str = ""


class DecisionResponse(BaseModel):
    id: uuid.UUID
    hypothesis: str
    probability: Decimal
    confidence: Decimal
    status: DecisionStatus
    decision_type: DecisionType | None
    expected_return: Decimal | None
    expected_drawdown: Decimal | None
    expected_utility: Decimal | None
    position_size: Decimal | None
    portfolio_impact: str | None
    assumptions: list[str]
    invalidation_conditions: list[str]
    explanation: str | None
    evidence: list[EvidenceOut]
    risk_assessment: RiskAssessmentModel | None
    review_history: list[ReviewRecordOut]
    created_at: datetime


# -- portfolios ---------------------------------------------------------------


class PortfolioCreateRequest(BaseModel):
    base_currency: Currency
    cash: Decimal = Field(ge=0)


class PositionOut(BaseModel):
    ticker: str
    quantity: Decimal
    average_cost: Decimal
    market_value: Decimal
    unrealized_pnl: Decimal
    currency: Currency


class PortfolioResponse(BaseModel):
    id: uuid.UUID
    owner_id: uuid.UUID
    base_currency: Currency
    cash: Decimal
    allocation: Decimal
    positions: list[PositionOut]


class CompanyResponse(BaseModel):
    id: uuid.UUID
    ticker: str
    name: str
    exchange: str
    sector: str
    industry: str
    currency: Currency
    status: str
    created_at: datetime


# -- market (contract only until ALG-001) --------------------------------------


class MarketContextResponse(BaseModel):
    regime: Regime
    confidence: Decimal
    liquidity_score: Decimal
    breadth_score: Decimal
    volatility_score: Decimal
    rotation_score: Decimal
    timestamp: datetime
