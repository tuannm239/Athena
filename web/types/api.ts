/**
 * TypeScript types mirroring the Athena backend REST contract (SPEC-08).
 * These are hand-authored from the backend Pydantic schemas
 * (`backend/api/schemas.py`) — the single source of truth for the wire
 * format. Do NOT add fields the backend does not send.
 */

/** SPEC-08 standard response envelope. */
export interface Envelope<T> {
  request_id: string;
  timestamp: string;
  status: "ok" | "error";
  data: T | null;
  errors: ApiError[] | null;
}

export interface ApiError {
  code: string;
  detail: string;
}

export interface Page<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

// --- auth ---
export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export type Role = "VIEWER" | "ANALYST" | "ADMIN";

export interface UserResponse {
  id: string;
  email: string;
  status: string;
  role: Role;
  created_at: string;
}

export interface ApiKeyResponse {
  id: string;
  name: string;
  prefix: string;
  created_at: string;
  revoked_at: string | null;
}

export interface ApiKeyCreatedResponse extends ApiKeyResponse {
  api_key: string; // shown once
}

// --- decisions (ADR-0006 evidence, SPEC-04 decision) ---
export type EvidenceDirection = "SUPPORTING" | "CONTRADICTING" | "NEUTRAL";
export type DecisionStatus = "DRAFT" | "UNDER_REVIEW" | "APPROVED" | "REJECTED" | "ARCHIVED";
export type DecisionType = "ENTRY" | "EXIT" | "REBALANCE" | "HOLD" | null;
export type RiskLevel = "VERY_LOW" | "LOW" | "MODERATE" | "HIGH" | "CRITICAL";

export interface EvidenceOut {
  id: string;
  source: string;
  category: string;
  explanation: string;
  reliability: string; // Decimal-as-string
  direction: EvidenceDirection;
  metadata: Record<string, string>;
  timestamp: string;
}

export interface RiskAssessmentModel {
  var: string;
  cvar: string;
  max_drawdown: string;
  stress_score: string;
  liquidity_score: string;
  level: RiskLevel;
  confidence: string;
}

export interface ReviewRecordOut {
  outcome: DecisionStatus;
  at: string;
  note: string;
}

export interface DecisionResponse {
  id: string;
  hypothesis: string;
  probability: string;
  confidence: string;
  status: DecisionStatus;
  decision_type: DecisionType;
  expected_return: string | null;
  expected_drawdown: string | null;
  expected_utility: string | null;
  position_size: string | null;
  portfolio_impact: string | null;
  assumptions: string[];
  invalidation_conditions: string[];
  explanation: string | null;
  evidence: EvidenceOut[];
  risk_assessment: RiskAssessmentModel | null;
  review_history: ReviewRecordOut[];
  created_at: string;
}

export interface EvidenceIn {
  source: string;
  category: string;
  explanation: string;
  reliability: number;
  direction: EvidenceDirection;
  metadata?: Record<string, string>;
}

export interface DecisionCreateRequest {
  hypothesis: string;
  probability: number;
  confidence: number;
  decision_type?: DecisionType;
  expected_return?: number | null;
  expected_drawdown?: number | null;
  assumptions?: string[];
  invalidation_conditions?: string[];
  evidence?: EvidenceIn[];
}

export interface DecisionUpdateRequest {
  explanation?: string | null;
  assumptions?: string[] | null;
  invalidation_conditions?: string[] | null;
  add_evidence?: EvidenceIn[];
  risk_assessment?: RiskAssessmentModel | null;
  status?: DecisionStatus | null;
  review_note?: string;
}

// --- portfolios ---
export interface PositionOut {
  ticker: string;
  quantity: string;
  average_cost: string;
  market_value: string;
  unrealized_pnl: string;
  currency: string;
}

export interface PortfolioResponse {
  id: string;
  owner_id: string;
  base_currency: string;
  cash: string;
  allocation: string;
  positions: PositionOut[];
}

// --- companies ---
export interface CompanyResponse {
  id: string;
  ticker: string;
  name: string;
  exchange: string;
  sector: string;
  industry: string;
  currency: string;
  status: string;
  created_at: string;
}

// --- market (contract; 501 until ALG-001 data lands) ---
export type Regime = "EXPANSION" | "RECOVERY" | "CONSOLIDATION" | "CONTRACTION";

export interface MarketContextResponse {
  regime: Regime;
  confidence: string;
  liquidity_score: string;
  breadth_score: string;
  volatility_score: string;
  rotation_score: string;
  timestamp: string;
}

// --- ops ---
export interface HealthFull {
  status: "ok" | "degraded";
  version: string;
  components: Record<string, string>;
}
