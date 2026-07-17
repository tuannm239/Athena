# Traceability Matrix

Chain: RFC/SPEC → module → package → class(es) → tests.
Rows marked **planned** gain code references when their sprint lands.
No implementation may exist without a row here.

## Implemented

| Document | Module | Package | Classes | Tests |
|---|---|---|---|---|
| SPEC-03 §Value Objects | shared kernel | `shared_kernel` | `Probability`, `Confidence`, `ProbabilityDistribution`, `Money`, `Currency`, `Percentage`, `PositionSize`, `TimeRange` | `tests/unit/test_domain.py::TestValueObjects`, `TestMoney` |
| SPEC-03 §Entities/Invariants, SPEC-04 §Business Rules | Decision | `decision_kernel.domain` | `Decision`, `DecisionStatus`, `DecisionType`, `ReviewRecord`, `Evidence` | `TestDecisionLifecycle` |
| SPEC-03 §Repository Interfaces | Decision | `decision_kernel.domain.repository` | `DecisionRepository` | interface — impl tests in Sprint 2 (S2-09) |
| SPEC-03 §Domain Events | all contexts | `*.domain.events`, `shared_kernel.events` | `DomainEvent`, `DecisionCreated`, `DecisionReviewed`, `EvidenceAdded`, `PortfolioUpdated`, `RiskCalculated`, `MarketRegimeChanged`, `LiquidityChanged`, `BreadthChanged`, `VolatilityChanged`, `BehaviorDetected` | `TestDecisionLifecycle::test_full_lifecycle` |
| SPEC-05 §Outputs/Regimes | Market | `market.domain` | `MarketContext`, `Regime`, `Instrument`, `PricePoint`, `MarketRepository` | `TestMarket` |
| SPEC-03 §Company | Company | `company.domain` | `Company`, `CompanyRepository` | construction covered via `TestIdentity`-style unit rules (extended in Sprint 2) |
| SPEC-03 §Portfolio/Position, SPEC-10 §Constraints/Rules | Portfolio | `portfolio.domain` | `Portfolio`, `Position`, `PortfolioConstraints`, `PortfolioRepository` | `TestPortfolio` |
| SPEC-03 §RiskAssessment, SPEC-11 §Levels/Outputs | Risk | `risk.domain` | `RiskAssessment`, `RiskLevel`, `RiskReport` | `TestRisk` |
| SPEC-12 §Biases/Journal/Outputs | Behavior | `behavior.domain` | `BiasKind`, `BehaviorReport`, `DecisionJournalEntry` | `TestBehavior` |
| SPEC-03 §Research, SPEC-01 §Research | Research | `research.domain` | `ResearchSummary`, `ResearchRepository` | Sprint 2 impl tests |
| SPEC-07 §users | Identity | `identity.domain` | `User` | `TestIdentity` |
| SPEC-08 §Standard Response/Error Codes | API | `api.envelope`, `api.errors` | `Envelope`, `RequestIdMiddleware`, `register_error_handlers` | `test_api.py::TestEnvelope` |
| SPEC-08 §Authentication (ADR-0009) | Identity | `identity.application`, `infrastructure.security` | `RegisterUser`, `AuthenticateUser`, `Argon2PasswordHasher`, `JwtTokenService`, `SqlCredentialStore` | `test_api.py::TestAuth` |
| SPEC-08 §Decisions | Decision | `decision_kernel.application`, `api.routes.decision` | `DecisionUseCases`, router | `test_api.py::TestDecisionsResource` |
| SPEC-08 §Portfolios | Portfolio | `portfolio.application`, `api.routes.portfolio` | `PortfolioUseCases`, router | `test_api.py::TestPortfoliosResource` |
| SPEC-08 §Companies/Market/Backtesting (contract) | API | `api.routes.{companies,market,backtests}` | routers (501 until engines) | `test_api.py::TestSpecPathsPending` |
| SPEC-03 events via application layer (ADR-0010) | shared | `shared_kernel.ports`, `infrastructure.events` | `EventPublisher`, `InProcessEventBus` | covered via use-case tests |
| RFC-0023 §4–§8 | Feature Store | `feature_store.domain`, `feature_store.application`, `infrastructure.db.repositories.feature_registry` | `FeatureMetadata`, `Feature`, `FeatureStatus`, `FeatureRegistry`, `SqlFeatureRegistry`, `FeatureStoreUseCases` | `tests/unit/test_feature_store.py`, `test_data_platform.py::TestFeatureRegistry` |
| SPEC-06 §Categories/Registration | Factor Library | `feature_store.domain.factor_catalogue` | `canonical_factors` (26 defs) | `test_feature_store.py::TestFactorCatalogue` |
| RFC-0024 §4–§10 | Data Pipeline | `data_pipeline.domain`, `data_pipeline.application`, `infrastructure.db.repositories.dataset_catalog` | stages, `DatasetSchema`, `QualityReport`, `Lineage`, `DatasetVersion`, DP001–005 errors, `DataPipelineUseCases`, `SqlDatasetCatalog` | `tests/unit/test_data_pipeline.py`, `test_data_platform.py::TestDataPipelineEndToEnd` |
| SPEC-11 §Scenario Analysis (ALG-015, ADR-0016) | Risk | `risk.domain.scenario` | `Scenario`, `builtin_scenarios`, `StressPosition`, `stress_test`, `StressResult` | `tests/unit/test_scenario_simulator.py` |
| SPEC-09 (ALG-013, ADR-0015) | Backtest | `backtest.domain.{metrics,simulator}` | `PerformanceMetrics`, `compute_metrics`, `BacktestEngine`, `BacktestReport` | `tests/unit/test_backtest_engine.py` |
| SPEC-12 (ALG-014, ADR-0014) | Behavior Engine | `behavior.domain.engine`, `behavior.domain.repository`, `infrastructure.db.repositories.journal` | `ClosedDecision`, `BehaviorThresholds`, `analyze`, `calibration_error`, `compute_kpis`, `SqlJournalRepository` | `tests/unit/test_behavior_engine.py`, `test_persistence.py::TestJournalRepository` |
| SPEC-04 + RFC-0020 §6 (ALG-012, ADR-0013) | Decision Kernel | `decision_kernel.application.kernel`, `decision_kernel.domain.decision_object` | `DecisionKernel`, `KernelInput`, `DecisionObject`, `KernelExplanation` | `tests/unit/test_decision_kernel.py` |
| RFC-0020 (ALG-011) | Decision Compiler | `dsl.domain.{ir,graph,compiler,evaluator}` | `RuleIR`, `DecisionGraph`, `CompiledRuleset`, `compile_rules`, `evaluate` | `tests/unit/test_dsl_compiler.py` (golden regression) |
| RFC-0017 v2 (ALG-010) | Decision DSL | `dsl.domain` | `tokenize`, `parse`, AST nodes, `SemanticAnalyzer`, `DEFAULT_SCHEMA`, DSL001–015 errors | `tests/unit/test_dsl_frontend.py` (golden + 46 more) |
| RFC-0027 §5 + SPEC-10 (ALG-007/008) | Portfolio | `portfolio.domain.sizing`, `portfolio.domain.optimizer` | `kelly_fraction`, `position_size`, `Candidate`, `propose_portfolio`, `PortfolioProposal` | `tests/unit/test_portfolio_engine.py` |
| RFC-0027 (SPEC-11, ALG-006) | Risk | `risk.domain.metrics`, `risk.domain.engine` | metric calculators, `RiskMetrics`, `risk_score`, `level_for`, `build_assessment`, `build_report` | `tests/unit/test_risk_engine.py` |
| RFC-0025 (SPEC-05, ALG-001) | Market | `market.domain.regime_engine`, `market.application`, `infrastructure.market_repository` | `RegimeInputs`, `market_score`, `classify`, `regime_confidence`, `MarketUseCases`, `InMemoryMarketRepository`, `RedisMarketRepository` | `tests/unit/test_regime_engine.py` |
| RFC-0018 + RFC-0026 (ADR-0006) | Probability | `probability.domain`, `probability.application` | `ProbabilityEngine`, `bayesian_update`, `confidence`, `expected_utility`, `ProbabilityReport`, PE errors, `ProbabilityUseCases` | `tests/unit/test_probability_engine.py`, `test_persistence.py::TestProbabilityOverStoredDecision` |
| Executive Directive (companies) | Company | `company.domain`, `infrastructure.db.repositories.company`, `api.routes.companies` | `Company`, `SqlCompanyRepository`, profile endpoint | `test_api.py::TestSpecPathsPending::test_unknown_company_profile_is_404` |
| RFC-0019 §3–§9 (ADR-0007) | Knowledge Graph | `knowledge.domain`, `knowledge.application`, `infrastructure.db.repositories.graph_store` | `Node`, `Edge`, `GraphSnapshot`, `ALLOWED_RELATIONS`, traversal services, `KnowledgeGraphUseCases`, `SqlGraphStore` | `tests/unit/test_knowledge_graph.py`, `tests/integration/test_knowledge_store.py` |
| SPEC-07 §Core Tables/Indexing | Infrastructure | `infrastructure.db.models` | `UserRow`, `PortfolioRow`, `PositionRow`, `DecisionRow`, `EvidenceRow`, `FactorRow` | `tests/integration/test_persistence.py` |
| SPEC-07 §Audit | Infrastructure | `infrastructure.db.repositories._audit`, `models.AuditRow` | `write_audit`, `AuditRow` | `test_persistence.py::TestDecisionRepository::test_updates_write_audit_records` |
| SPEC-03 §Repository Interfaces, SPEC-07 (impl) | Infrastructure | `infrastructure.db.repositories` | `SqlDecisionRepository`, `SqlPortfolioRepository`, `SqlUserRepository` | `tests/integration/test_persistence.py` |
| SPEC-07 §Migration | Infrastructure | `infrastructure.alembic` | `env.py`, revision `ec77f528e384` | CI step `alembic upgrade head` |
| SPEC-07 §DuckDB (immutable snapshots) | Infrastructure | `infrastructure.duckdb_store` | `DuckDbSnapshotStore` | `tests/unit/test_infrastructure.py::TestDuckDbSnapshotStore` |
| SPEC-07 §Redis (ephemeral state) | Infrastructure | `infrastructure.cache` | `RedisCache` | `tests/unit/test_infrastructure.py::TestRedisCache` (CI) |
| SPEC-07 §users + SPEC-08 auth need | Identity | `identity.domain.repository` | `UserRepository` | `test_persistence.py::TestUserRepository` |
| Phase 2 M1 — Data Provider SDK (RFC-0024 sources seam) | Providers | `providers.sdk` | ten capability Protocols, immutable DTOs, `Capability`, `ProviderRegistry` | `tests/unit/test_provider_sdk.py` |
| Phase 2 M2 — Provider Connectors | Providers | `providers.connectors` | `RetryPolicy`, `TokenBucketRateLimiter`, `TtlCache`, `HealthMonitor`, `StaticProvider`, `LocalFileProvider`, `ResilientPriceProvider` | `tests/unit/test_provider_connectors.py` |
| Phase 2 M3 — Production Data Pipeline (RFC-0024 §9, ADR-0017) | Data Pipeline / Knowledge | `data_pipeline.application.{sync,facts}`, `knowledge.application.sync` | `ProviderSyncService`, `SyncError`, dataset schemas, `PublishedPriceFacts`, `KnowledgeSyncService` | `tests/unit/test_production_sync.py` |
| Phase 2 M4 — LLM Gateway (ADR-0003, SPEC-00 LLM Policy) | LLM Gateway | `llm_gateway.domain`, `llm_gateway.application.gateway`, `llm_gateway.adapters`, `llm_gateway.testing` | `LlmClient`, `LlmGateway`, `LlmLineage`, `EvidenceDraft`, vendor adapters, `create_client`, `FakeLlmClient` | `tests/unit/test_llm_gateway.py`, `test_architecture.py` (isolation both directions) |
| Phase 2 M5 — Research Copilot (SPEC-01 Research, ADR-0003) | Research | `research.application.copilot` | `ResearchCopilot`, `ReviewedDraft`, `ResearchPacket`, `ResearchError` | `tests/unit/test_research_copilot.py` |
| Phase 2 M6 — Observability (ADR-0018) | Infrastructure / API | `infrastructure.metrics`, `api.envelope`, `api.main` (`/metrics`, `/health/full`), `ops/` | `Metrics`, `RequestIdMiddleware` metrics recording, Prometheus/Grafana provisioning | `tests/integration/test_observability_api.py` |
| Phase 2 M7 — Security (ADR-0019, SPEC-08) | Identity / API / Infrastructure | `identity.domain.user` (Role), `identity.application.{ports,use_cases}`, `api.{deps,ratelimit}`, `infrastructure.{config,security}`, `infrastructure.db.repositories.security_stores`, migration 0008 | `Role`, `require_roles`, `ApiKeyService`, `SqlApiKeyStore`, `SqlRefreshTokenStore`, `SqlSecurityAuditLog`, `RateLimiter`, `InsecureConfigurationError` | `tests/integration/test_security.py` (10 tests) |
| Phase 2 M8 — Performance | Tooling | `scripts/benchmark.py`, `docs/BENCHMARKS.md` | `bench`, `BenchResult`, `run` | `tests/unit/test_benchmark_smoke.py` |

## Planned

| Document | Module | Package (planned) | Key classes (planned) | Tests (planned) | Sprint |
|---|---|---|---|---|---|
| SPEC-08 | API/Auth | `api`, `identity.application` | envelope, error mapper, JWT auth | endpoint integration tests | 3 |
| SPEC-10 §Rebalancing | Portfolio Engine | `portfolio.application` | rebalancer over proposals | rebalance reproducibility tests | 13+ |
