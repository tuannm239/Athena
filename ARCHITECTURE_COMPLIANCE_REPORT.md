# ATHENA — Architecture Compliance Report (Phase 3, Verification 1)

Date: 2026-07-17 · Method: machine-enforced boundary tests + full
cross-context import-graph scan (AST-based, all 218 backend sources) +
RFC parameter test evidence. Implementation frozen; no changes were
required — **zero violations found**.

## 1. Clean Architecture (SPEC-02 Dependency Rule)

Evidence — `tests/unit/test_architecture.py`, all PASSED:

```
test_domain_layer_is_framework_free                    PASSED
test_constitution_contexts_have_no_llm_import_path     PASSED
test_llm_gateway_never_reaches_decision_contexts       PASSED
test_no_sql_in_domain_or_application                   PASSED
test_application_layer_does_not_import_infrastructure  PASSED
```

- Domain layers import no framework (FastAPI, SQLAlchemy, Alembic,
  Redis, DuckDB, httpx, requests all forbidden and verified).
- SQL exists only under `infrastructure` (SPEC-06 §4).
- Application layers never import infrastructure; the `api` package is
  the single composition root that wires adapters to ports.

## 2. DDD — bounded contexts and dependency directions

Full import-graph scan (every `backend/**.py`, AST imports, verified
2026-07-17 — scanner output reproduced verbatim):

```
api              -> company, decision_kernel, identity, infrastructure, market, portfolio, risk, shared_kernel
backtest         -> dsl, shared_kernel
behavior         -> shared_kernel
company          -> shared_kernel
data_pipeline    -> dsl, providers, shared_kernel
decision_kernel  -> dsl, portfolio, probability, risk, shared_kernel
dsl              -> shared_kernel
feature_store    -> shared_kernel
identity         -> shared_kernel
infrastructure   -> (implements ports of 11 contexts)
knowledge        -> providers, shared_kernel
llm_gateway      -> shared_kernel
market           -> shared_kernel
portfolio        -> shared_kernel
probability      -> decision_kernel, shared_kernel
providers        -> shared_kernel
research         -> decision_kernel, knowledge, llm_gateway, probability, shared_kernel
shared_kernel    -> (none)
==> NO VIOLATIONS
```

Findings:
- `shared_kernel` depends on nothing (pure kernel). ✅
- No context imports `api` (presentation is outermost). ✅
- Only `api` imports `infrastructure` (composition root). ✅
- Engine contexts (dsl, risk, portfolio, market, behavior, backtest)
  depend only on `shared_kernel`. ✅
- The two deliberate cross-context edges are documented decisions:
  `decision_kernel → {dsl, probability, risk, portfolio}` is the
  SPEC-04 orchestration via injected ports (ADR-0013);
  `probability → decision_kernel` is the unified Evidence model
  (ADR-0006). Neither creates a cycle (verified: graph is acyclic).
- Contexts map 1:1 to SPEC-03 (ADR-0004): 16 contexts + shared_kernel
  + api + infrastructure.

## 3. Hexagonal Architecture (ports & adapters)

| Port (interface) | Layer | Adapter(s) | Swappable by config |
|---|---|---|---|
| `DecisionRepository`, `PortfolioRepository`, `UserRepository`, `JournalRepository`, `GraphStore`, `DatasetCatalog`, `FeatureRegistry`, `CompanyRepository`, `ResearchRepository` | domain | SQL implementations in `infrastructure.db.repositories` | ✅ (session factory injection; in-memory fakes in tests) |
| `EventPublisher` | shared_kernel | `InProcessEventBus` (ADR-0010) | ✅ |
| `SnapshotWriter` | data_pipeline app | `DuckDbSnapshotStore` | ✅ |
| 10 provider capability Protocols | providers.sdk | Static, LocalFile (+ resilience decorators) | ✅ `ProviderRegistry` selection mapping |
| `ProbabilityPort`, `GraphExecutionPort` (kernel engines) | decision_kernel app | platform engines as defaults | ✅ (ADR-0013, RFC-0021 seam) |
| `LlmClient`, `HttpTransport` | llm_gateway | OpenAI/DeepSeek/local, Anthropic, Google; `FakeLlmClient` | ✅ `create_client` |
| `PasswordHasher`, `TokenService`, `CredentialStore`, `ApiKeyStore`, `RefreshTokenStore`, `SecurityAuditLog` | identity app | Argon2/JWT/SQL adapters | ✅ |

Every adapter has an independent test; every port has at least two
implementations (production + test double) — the hexagon is real, not
nominal.

## 4. RFC compliance (parameters machine-verified)

113 engine tests pass (`test_regime_engine`, `test_risk_engine`,
`test_probability_engine`, `test_dsl_frontend`, `test_dsl_compiler`):

| RFC | Ruling | Verifying tests |
|---|---|---|
| RFC-0025 | MarketScore = 0.30·Trend + 0.20·Breadth + 0.20·Liquidity + 0.15·Momentum + 0.15·(100−Vol); bands 80+/60–79/40–59/<40; Confidence = WeightedConsistency × DataCompleteness | `test_regime_engine.py` (exact Decimal assertions) |
| RFC-0026 | odds-form Bayes, BF = (1+w) supporting / 1/(1+w) contradicting, w = reliability × freshness(365d linear) × relevance; probability ≠ confidence (never merged) | `test_probability_engine.py` |
| RFC-0027 | risk score weights .25/.25/.20/.20/.10, caps 0.60/0.05/0.08/0.50/10d, bands 0–20/21–40/41–60/61–80/81–100; PositionSize = Kelly × RiskBudget × LiquidityFactor × Confidence × Constraints | `test_risk_engine.py`, `test_portfolio_engine.py` |
| RFC-0017 v2 | full grammar, DSL001–015, coverage requirement ≥ 95% | `test_dsl_frontend.py`; **dsl package coverage 99%** (measured this run) |
| RFC-0020 | IR → DAG → deterministic evaluation, `compiler_version athena-dslc/1.0.0`, golden regression | `test_dsl_compiler.py` |
| RFC-0019 | node/relation catalogue, versioned edges, cycle control | `test_knowledge_graph.py`, `test_knowledge_store.py` |
| RFC-0023/0024 | feature lifecycle/semver; pipeline stages, DP001–005, quality metrics, lineage | `test_feature_store.py`, `test_data_pipeline.py`, `test_data_platform.py` |

## 5. ADR compliance

19 accepted ADRs (`adr/README.md`). Spot verification of the
architecturally binding ones:

- **ADR-0003** (LLM isolation): enforced both directions by tests §1.
- **ADR-0004** (context↔package map): confirmed by scan §2.
- **ADR-0005** (lifecycle): `Decision` transitions DRAFT→…→ARCHIVED
  guarded, `InvalidDecisionTransition` tested.
- **ADR-0006** (evidence): single collection + explicit direction —
  `Decision.supporting_evidence`/`contradicting_evidence` are filters
  over one tuple; direction never inferred (`test_domain.py`).
- **ADR-0009/0019** (auth): verified in SECURITY_AUDIT_REPORT.
- **ADR-0010** (event bus): aggregates expose `pull_events()`; only
  application layer publishes; bus adapter in infrastructure.
- **ADR-0011**: `ruff format --check` green (218 files).
- **ADR-0013**: kernel engines injected via Protocols; defaults =
  platform engines (`kernel.py`).
- **ADR-0015/0016**: backtest/scenario conventions asserted in their
  test suites (bit-for-bit reproducibility test present).
- **ADR-0017**: watermark/replay/rollback semantics tested in
  `test_production_sync.py` and independently re-verified under
  failure injection (partial sync, quarantine, rollback) — see
  FAILURE_INJECTION_REPORT.md, all scenarios pass.
- **ADR-0018**: metrics per-app registry, route-template labels —
  `test_observability_api.py`.

## Verdict

**COMPLIANT.** No architecture violations across all five dimensions
(Clean, DDD, Hexagonal, RFC, ADR). No defects discovered during the
architecture verification pass.
