# Architecture Review Report — Phase 1

Date: 2026-07-15
Scope: all Markdown documents in the repository — `CLAUDE.md`, `IMPLEMENTATION_PLAN.md`,
`README.md`, SPEC-00…SPEC-12 in `/spec`, RFC-0018/0019/0020/0023/0024 in `/rfc`,
ADR-0001…0004 in `/adr` — plus the implemented code in `/backend` and `/tests`.

## 1. Implementation Status

| Phase | Status |
|---|---|
| Phase 3 — Sprint 0 bootstrap | **Done** (commit `49ed73a`) — uv/pyproject, FastAPI + 501 placeholders, SQLAlchemy/Alembic, Docker (PostgreSQL/DuckDB/Redis deps), ruff, mypy strict, pytest. Gaps: no CI workflow yet; Black replaced by ruff (see C8). |
| Phase 4 — Domain | **Done** (commit `a68ae33`) — entities, value objects, repository interfaces, domain events, exceptions per SPEC-03; ADR-0004 records context alignment. |
| Phase 5 — Infrastructure | Not started. |
| Phase 6 — Decision Platform | Not started; partially **blocked** (see C1). |

Quality gates at review time: ruff ✓, mypy strict ✓ (63 files), pytest ✓ (32 unit + integration).

## 2. Specification Dependency Graph

```text
SPEC-00 Constitution
  └─ SPEC-01 Product ─ SPEC-02 Architecture ─ SPEC-03 Domain Model
       ├─ SPEC-04 Decision Kernel ←─ RFC-0018 Probability, RFC-0020 Compiler (← RFC-0017 DSL, MISSING)
       ├─ SPEC-05 Market Engine  ←─ RFC-0023 Feature Store ← RFC-0024 Data Pipeline
       ├─ SPEC-06 Factor Library ←─ RFC-0023 Feature Store
       ├─ SPEC-07 Database ─ SPEC-08 API
       ├─ SPEC-09 Backtest ←─ RFC-0017 DSL (MISSING), SPEC-04
       ├─ SPEC-10 Portfolio ← SPEC-11 Risk ← SPEC-04
       ├─ SPEC-12 Behavior ← SPEC-04
       ├─ RFC-0019 Knowledge Graph ← RFC-0024 Data Pipeline
       ├─ RFC-0021 Plugin SDK (MISSING) ← SPEC-04 Extension Points
       └─ RFC-0022 Event Model (MISSING) ← all domain events
```

## 3. Conflicts and Ambiguities (must be resolved before the affected work)

**C1 — Missing required RFCs (blocker for Phase 6 steps 5–7).**
RFC-0017 Decision DSL, RFC-0021 Plugin SDK, and RFC-0022 Event Model are in the
required reading list and are referenced by other documents (RFC-0020 compiles
"Decision DSL"; SPEC-09 consumes "Decision DSL rules"; SPEC-04 Extension Points
imply the Plugin SDK; every context publishes domain events) but do not exist in
the repository. Feature Store, Knowledge Graph, Data Pipeline, and Probability
Engine (Phase 6 steps 1–4) are implementable without them; the DSL, Compiler,
and plugin work are not.

**C2 — Decision lifecycle differs between SPEC-03 and SPEC-04.**
SPEC-03: `Draft → UnderReview → Approved | Rejected → Archived`.
SPEC-04: `Draft → Evaluated → Reviewed → Approved → Archived` (no Rejected).
The implemented aggregate follows SPEC-03. A ruling is needed; if SPEC-04's
states are authoritative for the kernel, the aggregate needs an `Evaluated`
state and a migration of the transition map.

**C3 — Bounded-context sets differ between SPEC-02 and SPEC-03.**
SPEC-02 lists `…, Research, Identity, Notification` (no Behavior context, though
it defines a Behavior Engine component); SPEC-03 lists `…, Research, Behavior,
Identity` (no Notification). Code follows SPEC-03. Notification has no spec at
all — if it is a real context, it needs one.

**C4 — Decision Object field sets differ across SPEC-03, SPEC-04, RFC-0020.**
SPEC-04 adds `position_size`, `assumptions`, `invalidation_conditions`,
`explanation`; RFC-0020 adds `compiler_version` and `risk_assessment` but omits
`position_size`, `assumptions`, `invalidation_conditions`, `expected_return`,
`expected_drawdown`. The implemented entity carries the union of SPEC-03+04.
Recommend declaring RFC-0020's list the schema of a *compiled* Decision (with
`compiler_version`) layered on the SPEC-03/04 aggregate, and recording it in the
final RFC-0020 revision.

**C5 — Evidence model differs between SPEC-03 and RFC-0018.**
SPEC-03 Evidence: `source, category, description, confidence, timestamp`.
RFC-0018 Evidence: `source, category, timestamp, reliability, direction
(support/contradict)`. Two open mappings: is `reliability` the same value as
`confidence`? Is `direction` an Evidence attribute, or is it encoded by the
separate `evidence` / `counter_evidence` collections (as SPEC-03/04 imply and
the code implements)? Needs a ruling before RFC-0018 implementation.

**C6 — `CLAUDE.md` is stale relative to the canonical spec set.**
It still contains the draft-era decision pipeline with a "Behavioral Override"
stage (SPEC-12 v2 says the Behavior Engine is advisory and never overrides the
Decision Kernel), the draft Sprint-0 scope ("documents only"), and none of the
canonical spec numbering. Recommend regenerating `CLAUDE.md` from SPEC-00 and
the current repository state.

**C7 — Repository layout differs between SPEC-02 and ADR-0001/0004.**
SPEC-02 sketches a layer-first layout (`backend/domain, application,
infrastructure, api`); the implemented modular monolith is context-first
(`backend/<context>/domain`) per ADR-0001 and ADR-0004. The ADRs govern; SPEC-02
should be annotated at its next revision.

**C8 — Formatter: Black vs ruff.**
The operating prompt requires both Ruff and Black. Running both fights over
formatting. `ruff format` is the Black-compatible formatter already in the
toolchain; recommend adopting `ruff format --check` as the Black gate rather
than adding Black itself.

**C9 — Sprint/phase numbering differs across three documents.**
`IMPLEMENTATION_PLAN.md` (Sprint 2 = Application, 3 = Infrastructure, 4 = API,
5 = Kernel), SPEC-01 Release Strategy (Sprint 2 = Data platform, 3 = Kernel
MVP…), and the operating prompt's Phases (5 = Infrastructure, 6 = Decision
Platform in ten steps). One authoritative sequence is needed; the proposed order
in §5 follows the operating prompt, which is the most recent instruction.

## 4. Missing Specifications

1. RFC-0017 Decision DSL, RFC-0021 Plugin SDK, RFC-0022 Event Model (C1).
2. Notification context (C3).
3. Scenario Simulator (SPEC-01 product module 9) — named, never specified.
4. Authentication detail behind SPEC-08 (OAuth2/JWT flows, roles, token policy).
5. `PortfolioImpact` structure on the Decision object (currently free text).
6. Research context entities (ResearchSummary fields are a documented assumption).
7. CI pipeline definition (Phase 3 lists "CI configuration"; none exists yet).

## 5. Proposed Implementation Order (after approval)

1. **Phase 5 — Infrastructure**: SQLAlchemy models + repositories for Decision,
   Portfolio, Company, User (SPEC-07 tables); Alembic initial migration; DuckDB
   snapshot store; Redis cache adapter; integration tests against docker-compose.
   Add the missing CI workflow (ruff, ruff format, mypy, pytest) in the same phase.
2. **Phase 6.1 Feature Store** (RFC-0023) — registry, versioning, lifecycle.
3. **Phase 6.2 Knowledge Graph** (RFC-0019) — nodes/edges, traversal services.
4. **Phase 6.3 Data Pipeline** (RFC-0024) — ingestion→validation→publish, quality reports.
5. **Phase 6.4 Probability Engine** (RFC-0018) — after C5 ruling.
6. **Phase 6.5–6.7 DSL → Compiler → Decision Kernel** — blocked on RFC-0017 (C1) and C2/C4 rulings.
7. **Phase 6.8–6.10 Risk → Portfolio → Behavior Engines** (SPEC-11, SPEC-10, SPEC-12).

## 6. Risk Analysis

| Risk | Impact | Mitigation |
|---|---|---|
| Missing RFC-0017/0021/0022 discovered mid-Phase-6 | Rework of kernel/compiler | Blocked items sequenced last; obtain RFCs first (C1) |
| Divergent Decision schema (C2/C4/C5) | Schema churn across DB, API, kernel | Resolve rulings before Phase 5 persistence models |
| Stale `CLAUDE.md` steering future agents wrong | Wrong pipeline re-introduced | Regenerate from SPEC-00 (C6) |
| No CI | Gates only run locally | Add workflow in Phase 5 |
| ML/analytics deps (LightGBM, PyMC, Optuna) not yet pinned | Install surprises later | Pin when Probability Engine work starts |

---
**Verdict:** conflicts exist (C1–C9). Per the operating rules I stop here.
Phases 3–4 are complete and green; Phase 5 starts only after the rulings above.
