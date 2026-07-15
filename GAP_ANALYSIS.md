# GAP_ANALYSIS — ATHENA

Audit date: 2026-07-15. Ranking: Critical / High / Medium / Low.

## Missing Features

| # | Gap | Rank | Affected | Complexity |
|---|---|---|---|---|
| F1 | RFC-0017 Decision DSL, RFC-0021 Plugin SDK, RFC-0022 Event Model **documents do not exist** | **Critical** | compiler, kernel extension points, event dispatch | n/a — documents must be authored/uploaded |
| F2 | Decision evaluation pipeline (SPEC-04 steps 1–11) | Critical | decision_kernel | L (needs ALG-004/005/006 first) |
| F3 | Probability Engine (RFC-0018) | Critical | probability, kernel | L |
| F4 | Risk metrics VaR/CVaR/drawdown/tail/liquidity (SPEC-11, ALG-006) | Critical | risk | L |
| F5 | Feature Store + Factor Library (RFC-0023, SPEC-06, ALG-002/003) | High | feature_store | L |
| F6 | Data Pipeline (RFC-0024) | High | data_pipeline | L |
| F7 | Market regime detection ALG-001 (SPEC-05) | High | market | M |
| F8 | REST resources + auth (SPEC-08) | High | api, identity | L |
| F9 | Portfolio construction/sizing/optimizer (SPEC-10, ALG-007/008) | High | portfolio | L |
| F10 | Knowledge Graph (RFC-0019, ALG-009) | Medium | knowledge | L |
| F11 | Behavior engine detection/calibration (SPEC-12, ALG-014) | Medium | behavior | M |
| F12 | Backtest engine (SPEC-09, ALG-013) | Medium | backtest | L (needs RFC-0017 for DSL rules) |
| F13 | Scenario simulator (SPEC-01 module 9, ALG-015) — **no spec exists** | Medium | risk | unknown |
| F14 | LLM Gateway module (SPEC-00 policy, ADR-0003) | Medium | research | M |
| F15 | Notification context (SPEC-02 names it; no spec) | Low | — | unknown |
| F16 | Frontend (Next.js dashboard, SPEC-01 MVP) | Low (backend-first) | frontend | XL |
| F17 | Companies persistence — SPEC-07 defines no `companies` table yet SPEC-03 defines CompanyRepository | High (blocks SPEC-08 `/companies`) | company, infrastructure | S once ruled |

## Missing Tests

| # | Gap | Rank |
|---|---|---|
| T1 | PostgreSQL-dialect integration run is CI-only; no local docker profile documented | Medium |
| T2 | No property-based tests for Money/Probability arithmetic | Low |
| T3 | No contract tests for repository interfaces vs future implementations | Medium |
| T4 | No API auth/negative-path tests (auth not yet built) | High (lands with F8) |

## Missing Documentation

| # | Gap | Rank |
|---|---|---|
| D1 | **CLAUDE.md stale** — draft-era pipeline with "Behavioral Override" contradicting SPEC-12 v2; wrong Sprint-0 scope (C6) | **Critical** (misleads every future agent session) |
| D2 | AGENTS.md required by operating prompts but absent | High |
| D3 | Module READMEs (SPEC-02: "every module has its own README") | Medium |
| D4 | Backup/restore runbook (SPEC-07 §Backup) | Medium (Sprint 15) |

## Architecture Violations

None found. Verified: domain layer has zero imports of infrastructure /
FastAPI / SQLAlchemy (grep-verified, 0 hits); no SQL outside
`infrastructure`; controllers contain no business logic; no circular imports
(Risk↔Portfolio resolved by ADR-0005). Cross-context domain references
(decision_kernel → risk.RiskAssessment) are read-only published contracts —
allowed by SPEC-02 ("may not modify another context's aggregates").

## RFC Violations

| # | Item | Rank |
|---|---|---|
| R1 | SPEC-02 layer-first repo layout vs implemented context-first layout | Low — governed by ADR-0001/0004; annotate SPEC-02 at next revision |
| R2 | SPEC-02 lists Notification context; SPEC-03 lists Behavior — sets diverge (C3) | Medium — needs spec ruling |
| R3 | RFC-0018 Evidence(reliability, direction) vs SPEC-03 Evidence(confidence, two collections) (C5) | High — must be ruled before ALG-004 |

## Technical Debt

| # | Item | Rank |
|---|---|---|
| TD1 | No logging/observability anywhere (SPEC-00 DoD demands observability per feature) | High |
| TD2 | Repository save() uses delete-and-reinsert for aggregates — simple and correct, but O(n) churn and new evidence row ids on decision update come from domain ids (stable) while position ids regenerate | Medium |
| TD3 | `shared_kernel.lineage` (Lineage/SnapshotId/RunId) currently unused by production code — latent until Data Pipeline (RFC-0024 lineage) | Low — keep, wire in Sprint 4 |
| TD4 | Four bounded-decimal VOs repeat validation boilerplate (Probability/Confidence/Percentage/PositionSize) | Low |
| TD5 | `starlette.testclient` deprecation warning (httpx pin) | Low |
| TD6 | Decision aggregate exposes mutable public fields (e.g. `invalidation_conditions` assigned directly in tests) — invariants only enforced at transition time | Medium — tighten with setters in kernel sprint |
