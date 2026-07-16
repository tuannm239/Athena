# PROJECT_STATUS — ATHENA

Updated: 2026-07-16 (Sprint 16). Basis: 181 source files, 272 tests,
coverage 96% (gate ≥ 90%), migrations 0001–0007, CI green.

## Completion

**Backend platform: ~85%** of the specified scope. All sixteen directive
sprints are implemented; remaining work is exogenous (missing RFCs, data
feeds, frontend).

| Capability | State |
|---|---|
| Foundation, persistence, auth, SPEC-08 API | **Done** (Sprints 0–3) |
| Feature Store, Data Pipeline, Factor catalogue | **Done** (Sprint 4) |
| Knowledge Graph (versioned, explainable) | **Done** (Sprint 5) |
| Probability Engine (RFC-0026) | **Done** (Sprint 6) |
| Market Regime Engine (RFC-0025, ALG-001) | **Done** (Sprint 7) |
| Risk Engine (RFC-0027, ALG-006) | **Done** (Sprint 8) |
| Position Sizing + Optimizer (ALG-007/008) | **Done** (Sprint 9) |
| Decision DSL + Compiler (RFC-0017/0020, ALG-010/011) | **Done** (Sprints 10–11, dsl coverage 98.6%) |
| Decision Kernel (SPEC-04, ALG-012, ADR-0013) | **Done** (Sprint 12) |
| Behavior Engine (SPEC-12, ALG-014, ADR-0014) | **Done** (Sprint 13) |
| Backtest Engine (SPEC-09, ALG-013, ADR-0015) | **Done** (Sprint 14) |
| Scenario Simulator (ALG-015, ADR-0016) | **Done** (Sprint 15) |
| Hardening: structured logging + correlation ids, architecture boundary tests, runbook | **Done** (Sprint 16) |

## Known open items (not blocking the implemented scope)

1. **RFC-0021 Plugin SDK / RFC-0022 Event Model** — kernel extension seam
   (ADR-0013) and interim in-process bus (ADR-0010) await them.
2. **Market data feeds** — RFC-0024 sources are specified but no external
   provider adapters exist; /market and factor-value endpoints stay 501
   until data lands. ALG-002 factor *calculations* need those feeds.
3. **Auth roles & API keys** (ADR-0009 deferrals), Notification context
   (C3/ADR-0012), PyMC-backed calibration (replaces identity-v1), frontend
   (Next.js), LLM Gateway + Research Copilot surfaces.

## Traceability

Every implemented module has a row in `TRACEABILITY_MATRIX.md`; ADRs
0001–0016 (index `adr/README.md`); per-sprint history in `CHANGELOG.md`;
latest sprint detail in `SPRINT_REPORT.md`; operations in `docs/RUNBOOK.md`.
