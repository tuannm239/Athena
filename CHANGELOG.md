# Changelog

All notable changes to ATHENA. Format follows Keep a Changelog; versions are
pre-release sprints until Sprint 15 (production readiness).

## [Unreleased]

## Phase 2 Module 9 — Production Readiness (2026-07-16)

### Added
- `PRODUCTION_READINESS_REPORT.md`: architecture/security/performance
  compliance evidence, operational readiness, known risks, remaining
  technical debt, deployment recommendation and the Go/No-Go decision
  (**GO — conditional**: real market-data adapter, environment
  checklist + restore drill, CVE scanning).
- `docs/DR_PLAN.md` (RPO ≤ 1 h / RTO ≤ 4 h, four scenario procedures,
  replay-based snapshot recovery), `docs/DEPLOYMENT.md` (topology,
  config matrix, rollout, network policy, scheduled jobs, bootstrap),
  `docs/PRODUCTION_CHECKLIST.md` (go-live gates).
- RUNBOOK extended: metrics/health-dashboard operations, 429 triage,
  security-audit triage, quarantine replay/rollback procedures.
- PROJECT_STATUS refreshed (~95%; Phase 2 complete).

## Phase 2 Module 8 — Performance Benchmarks (2026-07-16)

### Added
- `scripts/benchmark.py`: deterministic benchmark suite for the four
  hot paths (DSL compile, decision-graph evaluation, probability
  engine over 30 evidence, KG impacts/traversal at 1k nodes, one-year
  weekly backtest) plus cold app startup — P50/P95/P99 latency,
  throughput, peak memory (tracemalloc); optional `--json` output.
- `docs/BENCHMARKS.md`: committed baseline with target assessment
  (all targets met with ≥10× headroom; kernel hot path 0.052 ms P95,
  startup 46 ms) and watchpoints (KG ≥100k nodes, intraday backtests).
- Smoke test keeps the suite runnable in CI.

## Phase 2 Module 7 — Security Hardening (2026-07-16)

### Added
- RBAC (ADR-0019): `Role` on the user (VIEWER/ANALYST/ADMIN),
  per-request role checks via `require_roles`, write endpoints guarded
  (VIEWER is read-only, 403 Forbidden mapped); role persisted
  (migration 0008) and exposed in the user response.
- API keys: `athena_…` keys with sha256-only storage, shown once at
  creation; X-API-Key authentication; list/revoke endpoints; revocation
  is a timestamp.
- Refresh-token rotation: single-use jti registry (`refresh_tokens`),
  reuse of a consumed token rejected and audited.
- Secret management: `ATHENA_ENV=production` refuses dev/short JWT
  secrets at startup (`InsecureConfigurationError`).
- Rate limiting: per-host token buckets, strict bucket for auth
  endpoints, 429 + Retry-After; `/health` and `/metrics` exempt
  (per-process interim — ADR-0019).
- Security audit trail: registrations, login success/failure, refresh
  rotation/rejection, API-key lifecycle → SPEC-07 audit log
  (`entity_type=security`); audit action column widened to 64.
- `docs/SECURITY_REVIEW.md`: OWASP Top 10 (2021) assessment with
  prioritized follow-ups.

## Phase 2 Module 6 — Observability (2026-07-16)

### Added
- Prometheus metrics (ADR-0018): per-app `Metrics` registry
  (`infrastructure.metrics`), `/metrics` exposition endpoint,
  HTTP request counter + latency histogram labeled by *route template*
  (bounded cardinality; unmatched requests share one label),
  `athena_app_info` version gauge; recorded in `RequestIdMiddleware`.
- `/health/full` component dashboard: database / Redis / snapshot-store
  status with aggregate ok/degraded (always 200 — reporting, not
  gating); `/health` stays a bare liveness probe.
- docker-compose Prometheus + Grafana with file-provisioned datasource
  and an ATHENA API dashboard (request rate, P95 latency, error share)
  under `ops/`.
- ADR-0018: metrics pull model; full OpenTelemetry SDK deferred until
  RFC-0022 / a second service (request-id correlation covers today's
  single-process path).
- `Container.sessions` exposed for health checks;
  `prometheus-client` runtime dependency.

## Phase 2 Module 5 — Research Copilot (2026-07-16)

### Added
- `ResearchCopilot` (`research.application.copilot`): the SPEC-01 flow
  Document → Evidence Extraction → KG → Evidence Objects → Probability
  Update → Decision Review. Ingest summarizes and extracts draft
  evidence via the LLM Gateway, persists the research summary and
  records EVENT→AFFECTS→COMPANY provenance in the knowledge graph.
  Reviewed drafts (human-set reliability, ADR-0003) become Evidence
  with LLM lineage metadata and land in the KG as EVIDENCE nodes with
  SUPPORTED_BY/CONTRADICTED_BY edges. Probability review reports
  without mutating the aggregate; decision review narrates structured
  facts. No method creates or transitions a decision (tested).
- `EvidenceInput.metadata` wired end-to-end (API `EvidenceIn.metadata`
  previously dropped on the inbound path).

## Phase 2 Module 4 — LLM Gateway (2026-07-16)

### Added
- `llm_gateway` context (ADR-0003): allowed-use-only façade
  (summarize / classify / explain / extract_evidence / generate_report —
  no decision-shaped method exists), every artifact lineage-tagged
  (source `llm`, model id, prompt version, task, timestamp).
- Vendor adapters over an injectable HTTP transport: OpenAI, DeepSeek
  and local OpenAI-compatible servers (one chat-completions dialect),
  Anthropic Messages, Google Gemini; configuration-driven
  `create_client` selection; `FakeLlmClient` for tests/offline dev.
- Architecture tests extended: guarded contexts now also include dsl,
  probability, market and backtest; new reverse guard proves
  `llm_gateway` never imports any guarded context.
- `httpx` promoted to a runtime dependency (gateway transport).

## Phase 2 Module 3 — Production Data Pipeline (2026-07-16)

### Added
- `ProviderSyncService` (ADR-0017): full/incremental/replay provider
  synchronization for prices, macro, fundamentals and FX through the
  unchanged RFC-0024 pipeline (quality gates, lineage, quarantine).
  Incremental watermarks recovered from the latest published dataset
  version — rollback automatically rewinds the watermark; replays land
  as `{end}#rN`, never overwriting history.
- `PublishedPriceFacts`: decision-pipeline bridge exposing published
  price/classification data as DSL fact mappings (Backtest
  `FactProvider`-compatible); no provider type crosses into guarded
  contexts.
- `KnowledgeSyncService`: idempotent KG company/sector sync
  materializing the RFC-0019 COMPANY→INDUSTRY→SECTOR chain.
- ADR index refreshed (0013–0017 rows).

## Phase 2 Module 2 — Provider Connectors (2026-07-16)

### Added
- Resilience toolkit (`providers.connectors.resilience`): RetryPolicy with
  exponential backoff and injectable sleeper, token-bucket rate limiter with
  injectable clock, TTL cache, per-provider HealthMonitor emitting the SDK
  `ProviderStatus`.
- `StaticProvider`: deterministic in-memory connector implementing all ten
  capability ports (tests, demos, offline development).
- `LocalFileProvider`: CSV-backed Price/Macro/FX/Sector/Calendar connector
  (polars) for locally staged datasets.
- `ResilientPriceProvider` decorator composing cache → rate limit → retry →
  health over any PriceProvider without the provider knowing.

## Phase 2 Module 1 — Data Provider SDK (2026-07-16)

### Added
- Ten framework-free capability ports (Price, Fundamental, Macro, News,
  CorporateAction, Calendar, Sector, ETF, FX, Commodity) with immutable
  Decimal DTOs (`providers.sdk`).
- Configuration-driven `ProviderRegistry` keyed by (capability, name);
  vendors are swappable via configuration only and no provider code can
  reach the domain (architecture-tested).

## Sprint 16 — Production hardening (2026-07-16)

### Added
- Structured JSON logging with request-id access logs and decision-id
  correlation; architecture boundary tests (domain purity, application/
  infrastructure separation, LLM isolation); operations runbook
  (docs/RUNBOOK.md); PROJECT_STATUS refresh.

## Sprint 15 — Scenario Simulator (2026-07-16)

### Added
- ALG-015 (SPEC-11, ADR-0016): configurable Scenario shocks, four built-in
  SPEC-11 parameter sets + user-defined scenarios, deterministic portfolio
  stress testing with per-position impacts and stressed liquidity.

## Sprint 14 — Backtest Engine (2026-07-16)

### Added
- ALG-013 (SPEC-09, ADR-0015): deterministic simulator (point-in-time
  universe, no look-ahead), eleven performance metrics incl. OLS
  alpha/beta, full report with equity/drawdown curves, monthly returns,
  trades and failure analysis.

## Sprint 13 — Behavior Engine (2026-07-16)

### Added
- ALG-014 (SPEC-12, ADR-0014): calibration (error + Brier), configurable
  detectors (overconfidence, confirmation bias, disposition effect),
  behavioral KPIs, behavior score, advisory recommendations; insert-only
  journal persistence (migration 0007).

## Sprint 12 — Decision Kernel (2026-07-16)

### Added
- ALG-012 (SPEC-04, ADR-0013): 11-step kernel pipeline over injected engine
  ports; Decision Object with all directive fields incl. compiler_version;
  six-facet explanation; LLM-import-free (ADR-0003 verified by test).

## Sprint 11 — Decision Compiler (2026-07-16)

### Added
- RFC-0020 back end: immutable IR, DAG Decision Graph with deterministic
  execution order and DSL009 cycle guard, compile_rules() pipeline with
  compiler version stamp, deterministic graph evaluator (fact matching,
  action semantics with unit-interval clamping, tags, explanations).

## Sprint 10 — Decision DSL front end (2026-07-16)

### Added
- RFC-0017 v2 committed; DSL context: deterministic lexer, recursive-descent
  parser (full v2 grammar), immutable AST, extensible property schema over
  the 12 root objects, semantic analyzer with DSL001–DSL015 error codes;
  golden example test; dsl package coverage 99%.

## Sprint 9 — Portfolio Engine (2026-07-16)

### Added
- ALG-007 (RFC-0027 §5): Kelly-based position sizing chain with [0,1]
  factor validation and constraint cap.
- ALG-008 (SPEC-10): deterministic utility-priority allocator enforcing
  position/sector/cash-reserve constraints; PortfolioProposal output with
  violations and explanation.

## Sprint 8 — Risk Engine (2026-07-16)

### Added
- ALG-006 (RFC-0027): volatility/VaR95/CVaR95/drawdown/downside-deviation/
  liquidity calculators (pure Decimal, 252-day lookback), weighted risk
  score with caps, five-level bands, assessment confidence min(1, n/252),
  RiskAssessment/RiskReport builders with risk-budget violation reporting.

## Sprint 7 — Market Regime Engine (2026-07-16)

### Added
- ALG-001 (RFC-0025): deterministic MarketScore, regime classification
  bands, WeightedConsistency × DataCompleteness confidence, MarketContext
  output; MarketRegimeChanged emitted only on regime change; in-memory and
  Redis MarketRepository adapters (SPEC-07 short-lived context).

## Sprint 6 — Probability Engine + Directive intake (2026-07-16)

### Added
- ADR-0006 evidence model across domain/persistence/API (explicit direction,
  reliability, explanation, metadata; migration 0005); RFC-0025/0026/0027;
  companies table + live company profile endpoint; CLAUDE.md regenerated;
  AGENTS.md created; RiskLevel re-banded per RFC-0027.
- Probability Engine (RFC-0026): deterministic Bayesian pipeline with
  freshness/relevance weighting, separate confidence, identity calibration,
  expected utility, ProbabilityReport with mandatory explanation, PE error
  codes, and evaluation over stored decisions.

## Sprint 5 — Knowledge Graph (2026-07-15)

### Added
- Knowledge context (RFC-0019): 10 node types (Evidence added by ADR-0007),
  9 directed relation types validated against the §4 catalogue, mandatory
  edge provenance, cycle control (explicit `allow_cycle` only).
- Deterministic reasoning services: FindNeighbors, FindImpacts,
  FindDependencies, Traverse, shortest path, ExplainRelationship with
  human-readable path rendering.
- Versioned `GraphStore` port + PostgreSQL adjacency implementation
  (ADR-0007): edges carry created/removed version ranges; any historical
  graph version is reconstructable and queryable.
- Migration 0004 (`kg_nodes`, `kg_edges`).

## Sprint 4 — Feature Store & Data Pipeline (2026-07-15)

### Added
- Feature Store context (RFC-0023): `FeatureMetadata` (semver-validated),
  lifecycle Draft→Validated→Published→Deprecated→Archived with publication
  gates (docs, tests, benchmark, owner), `FeatureRegistry` port + SQL
  implementation enforcing published-version immutability, read APIs
  (Get/GetVersion/List/Search), idempotent SPEC-06 factor catalogue seeding
  (26 factors across 7 categories).
- Data Pipeline context (RFC-0024): deterministic stages
  ingest→validate→normalize→quality with quarantine (nulls, duplicate keys,
  future timestamps), quality reports (completeness/accuracy/freshness/
  consistency/uniqueness), DP001–DP005 error codes, record-level lineage,
  `DatasetCatalog` port + SQL implementation, public interfaces RunPipeline/
  ValidateDataset/PublishDataset/RollbackDataset/GenerateQualityReport;
  datasets persist as immutable DuckDB snapshots; failed datasets never
  publish.
- Migration 0003 (`feature_definitions`, `datasets`).

## Sprint 3 — Application layer, auth & REST API (2026-07-15)

### Added
- Application layer: identity use cases (RegisterUser, AuthenticateUser),
  DecisionUseCases (create/get/list/update with lifecycle transitions),
  PortfolioUseCases; hexagonal ports (PasswordHasher, CredentialStore,
  TokenService, EventPublisher).
- JWT authentication (ADR-0009): Argon2id hashing, access/refresh pairs,
  `/api/v1/auth/register|login|refresh`; `password_hash` migration 0002.
- SPEC-08 REST resources: decisions (GET list/id, POST, PATCH), portfolios
  (GET list/id/positions, POST) — protected by bearer auth; standard response
  envelope with request-id middleware; full error-code mapping
  (400/401/404/409/422/501).
- SPEC-08 path alignment: companies, market, backtests routers expose spec
  paths returning 501 until their engines land; non-spec placeholder routers
  removed.
- In-process event bus (ADR-0010); pagination support in repositories.
- CTO audit reports: PROJECT_STATUS, GAP_ANALYSIS, IMPLEMENTATION_BACKLOG,
  ARCHITECTURE_REVIEW v2, CODE_QUALITY_REPORT.

### Changed
- `pyproject`: added `pyjwt`, `argon2-cffi`; B008 lint exemption for FastAPI
  dependency idiom.

## Sprint 2 — Persistence (2026-07-15)

### Added
- SQLAlchemy ORM models for SPEC-07 core tables (`users`, `portfolios`,
  `positions`, `decisions`, `evidence`, `factors`) plus immutable `audit_log`.
- Initial Alembic migration `ec77f528e384`; env wired to `Base.metadata`.
- Repository implementations: `SqlDecisionRepository`, `SqlPortfolioRepository`,
  `SqlUserRepository` (with `UserRepository` interface in the identity domain);
  every Decision/Portfolio mutation writes an audit record.
- `DuckDbSnapshotStore` — immutable, versioned analytical snapshots.
- `RedisCache` — cache + idempotency keys (ephemeral state only).
- Typed `Settings` config; CI workflow (ruff, ruff format, mypy, migrations,
  pytest with PostgreSQL/Redis services, coverage gate ≥ 90%).
- ADR-0005 (decision lifecycle/schema, Risk↔Portfolio contract),
  ADR-0011 (`ruff format` as the Black gate).

### Changed
- Codebase formatted with `ruff format` (style commit `f2f3efc`).
- `pyproject`: added `pyarrow`, `pytest-cov`.

## Sprint 1 — Domain model (2026-07-15, `a68ae33`)
- Canonical domain layer per SPEC-03/04/05/10/11/12; ADR-0004.
- Canonical specification set SPEC-00…12 adopted (`34c5b51`); Phase 1
  architecture review (`6eaefb4`); Phase 2 roadmap (`8bc4eb9`).

## Sprint 0 — Bootstrap (2026-07-14, `49ed73a`)
- Repository structure, uv/pyproject, FastAPI 501 skeleton, Docker,
  Alembic scaffold, pytest/ruff/mypy toolchain.
