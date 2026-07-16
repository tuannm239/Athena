# ATHENA Sprint Plan — Phase 2

Date: 2026-07-15 · Companion documents: `ARCHITECTURE_REVIEW.md` (Phase 1),
`TASK_PLAN.md` (task breakdown), `TRACEABILITY_MATRIX.md`, `adr/README.md` (ADR list).

## 1. Dependency Analysis

| Document | Required inputs | Produced outputs | Dependent modules | External deps | Blocking deps |
|---|---|---|---|---|---|
| SPEC-00 Constitution | — | governing rules | all | — | — |
| SPEC-01 Product | SPEC-00 | scope, MVP, sprints | all | — | — |
| SPEC-02 Architecture | SPEC-00/01 | layers, contexts, constraints | all | — | — |
| SPEC-03 Domain Model | SPEC-02 | entities, VOs, repos, events | every context | — | — |
| SPEC-04 Decision Kernel | SPEC-03, RFC-0018/0020 | Decision object contract | decision_kernel, backtest | — | C2/C4 rulings; RFC-0017 |
| SPEC-05 Market Engine | SPEC-03, RFC-0023/0024 | MarketContext | market, risk, probability | market/macro data feeds | data pipeline |
| SPEC-06 Factor Library | SPEC-03, RFC-0023 | factor definitions | feature store, company | fundamental data | RFC-0023 |
| SPEC-07 Database | SPEC-03 | schema, stores | infrastructure | PostgreSQL, DuckDB, Redis | — |
| SPEC-08 API | SPEC-03/07 | REST contract | api | OAuth2 provider | auth ADR |
| SPEC-09 Backtest | SPEC-04/10/11, RFC-0017 | metrics, reports | backtest | historical data | RFC-0017 (missing) |
| SPEC-10 Portfolio | SPEC-03/11 | Portfolio Proposal | portfolio | — | SPEC-11 contracts |
| SPEC-11 Risk | SPEC-03/05 | RiskAssessment/Report | risk, decision_kernel | — | market context contract |
| SPEC-12 Behavior | SPEC-03/04 | BehaviorReport, journal | behavior | — | decision events |
| RFC-0018 Probability | SPEC-03/05 | Probability Report | probability, decision_kernel | PyMC (later) | C5 ruling |
| RFC-0019 Knowledge Graph | SPEC-03, RFC-0024 | graph + traversal services | knowledge, decision_kernel | storage (ADR-0007) | data pipeline |
| RFC-0020 Compiler | RFC-0017, SPEC-04 | Decision Graph/Object | dsl_compiler | — | **RFC-0017 missing** |
| RFC-0023 Feature Store | SPEC-06, RFC-0024 | versioned features | feature_store, engines | DuckDB | — |
| RFC-0024 Data Pipeline | SPEC-07 | validated datasets | data_pipeline, feature_store | source providers | — |
| RFC-0017 DSL / 0021 Plugin SDK / 0022 Event Model | — | — | compiler, plugins, events | — | **NOT IN REPO (C1)** |

## 2. Module Dependency Matrix

`●` = row depends on column. Only domain/platform modules shown; `api` depends on all application services; everything depends on `shared_kernel`.

| module ↓ / on → | shr_krn | market | company | risk | portfolio | behavior | feat_store | kn_graph | data_pipe | probability | dsl_cmp | dec_kernel |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| market          | ● | — | | | | | ● | | ● | | | |
| company         | ● | | — | | | | ● | ● | ● | | | |
| risk            | ● | ● | | — | *ctr* | | ● | | | | | |
| portfolio       | ● | | | ● | — | | ● | | | | | |
| behavior        | ● | | | | | — | ● | | | | | ● |
| feature_store   | ● | | | | | | — | | ● | | | |
| knowledge_graph | ● | | | | | | | — | ● | | | |
| data_pipeline   | ● | | | | | | | | — | | | |
| probability     | ● | ● | | | | | ● | | | — | | |
| dsl_compiler    | ● | | | | | | | | | ● | — | |
| decision_kernel | ● | ● | ● | ● | ● | | ● | ● | | ● | ● | — |

**Cycle check.** The only apparent cycle is Risk ↔ Portfolio: SPEC-10's sequence has
Portfolio → Risk ("Validate Risk") while SPEC-11's sequence has Risk → Portfolio
("Validate Budget"). At module level this dissolves: SPEC-11 lists *Portfolio
State* (a data contract) as an input, not the Portfolio Engine. Ruling encoded as
*ctr* above: **risk depends only on the PortfolioState contract** (owned by the
portfolio context's published contracts), portfolio depends on the risk engine
service. No import cycle exists; therefore planning continues. This ruling will
be recorded as ADR-0005 when Sprint 2 begins.

## 3. Epic Breakdown

| Epic | Content | Specs | Sprints |
|---|---|---|---|
| E1 Foundation | repo, tooling, CI, Docker | SPEC-00/02 | 0 |
| E2 Domain | entities, VOs, events, repo interfaces | SPEC-03/04/05/10/11/12 | 1 |
| E3 Persistence | SQLAlchemy, Alembic, DuckDB, Redis | SPEC-07 | 2 |
| E4 API & Auth | REST v1, OAuth2/JWT, OpenAPI | SPEC-08 | 3 |
| E5 Data Platform | feature store + data pipeline | RFC-0023/0024, SPEC-06 | 4 |
| E6 Knowledge Graph | nodes, edges, traversal | RFC-0019 | 5 |
| E7 Probability | Bayesian update, calibration | RFC-0018 | 6 |
| E8 DSL & Compiler | grammar, lexer→IR | RFC-0017*, RFC-0020 | 7–8 |
| E9 Decision Kernel | evaluation pipeline | SPEC-04 | 9 |
| E10 Engines | risk, portfolio, behavior | SPEC-11/10/12 | 10–12 |
| E11 Hardening | integration, performance, production | SPEC-01/09 | 13–15 |

## 4. Sprint Breakdown

Each sprint ends independently deployable (all gates green, main releasable).

| Sprint | Scope | Status / Gate to start |
|---|---|---|
| 0 | Repository, tooling, Docker; **remaining:** CI workflow, `ruff format` gate (C8) | **Done** `49ed73a` — residuals folded into Sprint 2 |
| 1 | Domain model | **Done** `a68ae33` (ADR-0004) |
| 2 | Database & infrastructure: ORM models per SPEC-07, repository implementations, initial Alembic migration, DuckDB snapshot store, Redis adapter, audit records, CI | **Done** — ADR-0005 froze the decision schema |
| 3 | API & auth: real routers over application services, OAuth2/JWT, standard response envelope, pagination, OpenAPI publish | **Done** — ADR-0009/0010; OpenAPI artifact deferred to CI hardening |
| 4 | Feature Store + Data Pipeline (RFC-0023/0024) + Factor Library skeleton (SPEC-06) | **Done** |
| 5 | Knowledge Graph (RFC-0019) | ADR-0007 (graph storage) |
| 6 | Probability Engine (RFC-0018) | Ruling C5 (evidence model) |
| 7 | Decision DSL | **Blocked: RFC-0017 missing (C1)** |
| 8 | Decision Compiler (RFC-0020) | Sprint 7 |
| 9 | Decision Kernel (SPEC-04) | Sprints 6–8; rulings C2/C4 |
| 10 | Risk Engine (SPEC-11) | Sprint 4 (features), Sprint 2 |
| 11 | Portfolio Engine (SPEC-10) | Sprint 10 |
| 12 | Behavior Engine (SPEC-12) | Sprint 9 (decision events) |
| 13 | Integration: end-to-end decision flow, backtest hooks (SPEC-09 needs RFC-0017) | Sprints 9–12 |
| 14 | Performance: profiling, caching policy, analytical query tuning | Sprint 13 |
| 15 | Production readiness: observability, backups (SPEC-07), security review, docs | Sprint 14 |

## 5. Risk Register

| # | Risk | P | I | Mitigation | Owner gate |
|---|---|---|---|---|---|
| R1 | RFC-0017/0021/0022 absent when Sprint 7 starts | H | H | Sprints ordered so 2–6 proceed first; request docs now (C1) | Sprint 7 |
| R2 | Decision schema churn (C2/C4/C5 unresolved) | M | H | Freeze rulings via ADR-0005/0006 before Sprint 2 `decisions` table | Sprint 2 |
| R3 | Auth scope creep (SPEC-08 names OAuth2+roles+API keys) | M | M | ADR-0009 picks minimal JWT-first path; API keys deferred | Sprint 3 |
| R4 | Graph storage choice wrong (RFC-0019 demands storage independence) | M | M | Port/adapter behind `GraphStore` interface; ADR-0007 | Sprint 5 |
| R5 | ML deps (PyMC/LightGBM) bloat image, slow CI | M | L | Isolate in optional dependency group at Sprint 6 | Sprint 6 |
| R6 | Stale CLAUDE.md misleads future sessions (C6) | H | M | Regenerate from SPEC-00 upon approval | any |
| R7 | Risk↔Portfolio runtime loop regressions | L | M | Contract-only dependency (ADR-0005), contract tests both sides | Sprint 10 |
| R8 | Backtest bias (look-ahead/survivorship, SPEC-09) | M | H | Snapshot-pinned datasets from Sprint 4 onward; bias tests in Sprint 13 | Sprint 13 |

## 6. Standing Rules for Every Sprint

1. Tests, `ruff check`, `ruff format --check`, `mypy --strict` green before commit.
2. Docs updated in the same commit; ADR whenever §ADR triggers in `adr/README.md` fire.
3. Every task references its spec (see `TASK_PLAN.md`); every merged module lands
   a row in `TRACEABILITY_MATRIX.md`.
4. Stop at sprint end; wait for explicit approval.
