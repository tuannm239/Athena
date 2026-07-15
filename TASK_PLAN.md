# ATHENA Task Plan — Phase 2

Task rules: one objective, < 1 day, independently testable and reviewable.
Complexity: S (≤ 2h), M (≤ 4h), L (≤ 1 day). IDs are `S<sprint>-<nn>`.
Every task references its governing document(s). Sprints 0–1 are complete
(commits `49ed73a`, `a68ae33`) and are not re-broken-down here.

## Sprint 2 — Database & Infrastructure (SPEC-07)

| ID | Task & objective | Inputs → Outputs | Refs | Deps | Acceptance criteria | Cx |
|---|---|---|---|---|---|---|
| S2-01 | ADR-0005: decision lifecycle & Risk↔Portfolio contract ruling | C2/C4 analysis → accepted ADR | SPEC-03/04, SPEC-10/11 | user ruling | ADR merged; aggregate updated if ruling differs from SPEC-03 | S |
| S2-02 | CI workflow (GitHub Actions): ruff, ruff format, mypy, pytest | repo → `.github/workflows/ci.yml` | SPEC-06 §CI intent, C8 | — | CI green on push; failing gate blocks | S |
| S2-03 | Settings module: typed env config (DATABASE_URL, REDIS_URL, DUCKDB_PATH) | env vars → `infrastructure/config.py` | SPEC-07 | — | mypy strict; defaults match docker-compose | S |
| S2-04 | SQLAlchemy base + engine/session factory (sync, psycopg) | config → `infrastructure/db/engine.py` | SPEC-07 | S2-03 | session context manager unit-tested with SQLite-in-memory smoke | M |
| S2-05 | ORM models: `users`, `portfolios`, `positions` | SPEC-07 tables → `infrastructure/db/models/` | SPEC-07 §Core Tables | S2-04 | UUID PKs, UTC timestamps, indexes per spec | M |
| S2-06 | ORM models: `decisions`, `evidence`, `factors` | SPEC-07 tables → models | SPEC-07, ADR-0005 | S2-01, S2-04 | fields match frozen decision schema | M |
| S2-07 | Audit-record model + write-on-update hooks for Decision/Portfolio/Position | mutations → immutable audit rows | SPEC-07 §Audit | S2-05/06 | update produces audit row; rows immutable (no UPDATE path) | M |
| S2-08 | Initial Alembic migration (all Sprint-2 tables) | models → `versions/0001_*.py` | SPEC-07 §Migration | S2-05..07 | `alembic upgrade head` idempotent against fresh Postgres | M |
| S2-09 | `DecisionRepository` implementation + mapper domain↔ORM | interface → `infrastructure/repositories/decision.py` | SPEC-03, SPEC-07 | S2-06 | round-trip property: save→get reconstructs aggregate incl. evidence/history | L |
| S2-10 | `PortfolioRepository` + `CompanyRepository` + `UserRepository` implementations | interfaces → implementations | SPEC-03/07 | S2-05 | round-trip tests; no SQL outside infrastructure | L |
| S2-11 | DuckDB snapshot store: immutable dataset write/read by snapshot id | Polars frame → versioned .duckdb artifacts | SPEC-07 §DuckDB | S2-03 | same snapshot id ⇒ byte-identical reads; overwrite forbidden | M |
| S2-12 | Redis adapter: cache + idempotency key helpers | config → `infrastructure/cache.py` | SPEC-07 §Redis | S2-03 | TTL respected; integration test via docker-compose | S |
| S2-13 | Integration test suite vs docker-compose Postgres/Redis | S2-04..12 → `tests/integration/test_persistence.py` | SPEC-06 testing rules | S2-08..12 | suite green locally and in CI (services in CI) | M |

## Sprint 3 — API & Authentication (SPEC-08)

| ID | Task & objective | Inputs → Outputs | Refs | Deps | Acceptance criteria | Cx |
|---|---|---|---|---|---|---|
| S3-01 | ADR-0009: auth strategy (OAuth2 password/JWT first, API keys deferred) | SPEC-08 §Auth → ADR | SPEC-08 | user ruling | ADR accepted | S |
| S3-02 | Standard response envelope (request_id, timestamp, status, data, errors) | SPEC-08 §Standard Response → `api/envelope.py` | SPEC-08 | — | all handlers wrapped; schema in OpenAPI | M |
| S3-03 | Domain error → HTTP mapping middleware (422 BusinessRuleViolation etc.) | DomainError → error codes | SPEC-08 §Error Codes | S3-02 | mapping table unit-tested for every code | M |
| S3-04 | Auth: user registration/login, JWT issue/verify, role guard | identity domain → `/api/v1/auth/*` | SPEC-08, SPEC-07 users | S3-01, S2-10 | 401/403 paths tested; tokens expire; refresh flow | L |
| S3-05 | Decisions resource: GET list (paginated), GET by id, POST, PATCH | app services → `/api/v1/decisions*` | SPEC-08 §Decisions | S2-09, S3-02/03 | 501 placeholders replaced; integration tests per endpoint | L |
| S3-06 | Portfolios resource: GET list, POST, GET by id, GET positions | app services → `/api/v1/portfolios*` | SPEC-08 §Portfolios | S2-10 | pagination + filtering; tests | M |
| S3-07 | Companies + Market resources (read-only skeletons over repositories) | repos → `/api/v1/companies/*`, `/api/v1/market/*` | SPEC-08 | S2-10 | contract matches spec paths; 501 only where engine pending | M |
| S3-08 | OpenAPI publish: versioned JSON artifact + docs page check in CI | app → `openapi/v1.json` committed artifact | SPEC-08 §Principles | S3-05..07 | CI diff-checks artifact vs runtime schema | S |

## Sprint 4 — Feature Store & Data Pipeline (RFC-0023/0024, SPEC-06)

| ID | Task & objective | Inputs → Outputs | Refs | Deps | Acceptance criteria | Cx |
|---|---|---|---|---|---|---|
| S4-01 | Feature metadata model + registry (id, version, owner, method, deps, freshness) | RFC-0023 §4 → `feature_store` context | RFC-0023 | S2-11 | metadata validated; duplicate id+version rejected | M |
| S4-02 | Feature lifecycle: Draft→Validated→Published→Deprecated→Archived; published immutable | registry → lifecycle service | RFC-0023 §5 | S4-01 | illegal transitions raise; published values frozen | M |
| S4-03 | Read APIs: GetFeature/GetFeatureVersion/ListFeatures/SearchFeatures | registry → application services | RFC-0023 §6 | S4-01 | historical versions queryable | M |
| S4-04 | Pipeline stage framework: Ingestion→Validation→Normalization→Enrichment→QualityChecks with quarantine | RFC-0024 §4–5 → `data_pipeline` context | RFC-0024 | S2-11 | invalid records quarantined, never published | L |
| S4-05 | Dataset versioning + lineage metadata (source, pipeline version, steps) | stage outputs → versioned datasets | RFC-0024 §7 | S4-04 | every record traceable to source | M |
| S4-06 | Quality report generation (completeness, accuracy, freshness, consistency, uniqueness) | run → QualityReport | RFC-0024 §6 | S4-04 | report emitted per execution; failing dataset blocks publish | M |
| S4-07 | Public interfaces: RunPipeline/ValidateDataset/PublishDataset/RollbackDataset | services | RFC-0024 §9 | S4-04..06 | rollback restores prior version; deterministic re-run | M |
| S4-08 | Factor Library skeleton: factor metadata + registration validation suite | SPEC-06 → `factors` in feature store | SPEC-06 | S4-01 | new factor requires docs+tests+benchmark declaration | M |
| S4-09 | Market/company feature definitions v1 (regime, liquidity, breadth, volatility; ROE, growth…) as registered metadata (no calculations yet) | SPEC-05/06, RFC-0023 §3 → registry entries | RFC-0023 | S4-08 | entries published with owners and units | S |

## Sprint 5 — Knowledge Graph (RFC-0019)

| ID | Task & objective | Inputs → Outputs | Refs | Deps | Acceptance criteria | Cx |
|---|---|---|---|---|---|---|
| S5-01 | ADR-0007: graph storage (PostgreSQL adjacency vs dedicated store) behind `GraphStore` port | RFC-0019 §10 → ADR | RFC-0019 | user ruling | ADR accepted; port defined | S |
| S5-02 | Node/edge domain model: 8 node types, 10 typed directed relations, unique ids | RFC-0019 §3–4 → `knowledge` context | RFC-0019 | — | unknown relation types rejected; edges carry provenance | M |
| S5-03 | Versioned mutations: graph updates auditable, history queryable | mutations → versioned graph | RFC-0019 §8 | S5-01/02 | point-in-time query returns historical edges | L |
| S5-04 | Traversal services: FindNeighbors/FindImpacts/FindDependencies/Traverse | graph → deterministic traversals | RFC-0019 §6, §9 | S5-02 | deterministic ordering; cycle-safe | L |
| S5-05 | ExplainRelationship: path rendering with semantic edge types | path → explanation structure | RFC-0019 §9 | S5-04 | example of §7 reproduced in test | M |

## Sprint 6 — Probability Engine (RFC-0018)

| ID | Task & objective | Inputs → Outputs | Refs | Deps | Acceptance criteria | Cx |
|---|---|---|---|---|---|---|
| S6-01 | ADR-0006: evidence model unification (C5: reliability↔confidence, direction vs collections) | ruling → ADR + domain adjustment | SPEC-03, RFC-0018 | user ruling | ADR accepted; Evidence updated once | S |
| S6-02 | Prior/Likelihood/Posterior value objects with bounds | RFC-0018 §5 → `probability` context | RFC-0018 | S6-01 | out-of-range construction impossible | S |
| S6-03 | Evidence weighting (reliability, relevance, direction, freshness) | evidence set → weights | RFC-0018 §5 | S6-02 | deterministic weights; contradictory evidence never dropped | M |
| S6-04 | Bayesian update step (deterministic, no PyMC yet) | prior + likelihoods → posterior | RFC-0018 §4 | S6-03 | property tests: bounded, monotone in support, reproducible | L |
| S6-05 | Confidence calibration separate from probability | evidence quality → Confidence | RFC-0018 §6 | S6-03 | missing evidence lowers confidence; reported separately | M |
| S6-06 | Probability Report assembly (prior, posterior, confidence, summary, assumptions, uncertainty, utility, explanation) | pipeline → report object | RFC-0018 §8 | S6-04/05 | every report carries explanation; PE00x error codes | M |

## Sprints 7–15 — outline (detail after blockers clear)

| Sprint | Gate | Outline tasks |
|---|---|---|
| 7 DSL | **RFC-0017 required (C1)** | grammar, lexer, parser, source locations, DC001/002 errors |
| 8 Compiler | Sprint 7 | AST→semantic analysis→rule validator→IR→Decision Graph (RFC-0020 §3–5), DC003–007 |
| 9 Kernel | 6+8, rulings C2/C4 | SPEC-04 pipeline steps 1–11, decision types, explainability six-fields, extension points (needs RFC-0021) |
| 10 Risk | 2, 4 | SPEC-11 metrics (VaR/CVaR/drawdown/liquidity), levels+confidence, scenario framework, RiskReport |
| 11 Portfolio | 10 | SPEC-10 construction/sizing/rebalance, constraint validation, proposal + explanation |
| 12 Behavior | 9 | SPEC-12 journaling, bias detection over decision history, calibration tracking, KPIs |
| 13 Integration | 9–12 | end-to-end decision flow; backtest engine (SPEC-09) — needs RFC-0017 for DSL rules |
| 14 Performance | 13 | profiling, cache policy, DuckDB query tuning, load tests |
| 15 Production | 14 | observability (structured logs, metrics), backup/restore drill (SPEC-07 §Backup), security pass, docs freeze |
