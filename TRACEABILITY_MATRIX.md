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
| SPEC-07 §Core Tables/Indexing | Infrastructure | `infrastructure.db.models` | `UserRow`, `PortfolioRow`, `PositionRow`, `DecisionRow`, `EvidenceRow`, `FactorRow` | `tests/integration/test_persistence.py` |
| SPEC-07 §Audit | Infrastructure | `infrastructure.db.repositories._audit`, `models.AuditRow` | `write_audit`, `AuditRow` | `test_persistence.py::TestDecisionRepository::test_updates_write_audit_records` |
| SPEC-03 §Repository Interfaces, SPEC-07 (impl) | Infrastructure | `infrastructure.db.repositories` | `SqlDecisionRepository`, `SqlPortfolioRepository`, `SqlUserRepository` | `tests/integration/test_persistence.py` |
| SPEC-07 §Migration | Infrastructure | `infrastructure.alembic` | `env.py`, revision `ec77f528e384` | CI step `alembic upgrade head` |
| SPEC-07 §DuckDB (immutable snapshots) | Infrastructure | `infrastructure.duckdb_store` | `DuckDbSnapshotStore` | `tests/unit/test_infrastructure.py::TestDuckDbSnapshotStore` |
| SPEC-07 §Redis (ephemeral state) | Infrastructure | `infrastructure.cache` | `RedisCache` | `tests/unit/test_infrastructure.py::TestRedisCache` (CI) |
| SPEC-07 §users + SPEC-08 auth need | Identity | `identity.domain.repository` | `UserRepository` | `test_persistence.py::TestUserRepository` |

## Planned

| Document | Module | Package (planned) | Key classes (planned) | Tests (planned) | Sprint |
|---|---|---|---|---|---|
| SPEC-08 | API/Auth | `api`, `identity.application` | envelope, error mapper, JWT auth | endpoint integration tests | 3 |
| RFC-0019 | Knowledge Graph | `knowledge` | node/edge model, `GraphStore` port, traversal services | deterministic traversal tests | 5 |
| RFC-0018 | Probability | `probability` | `Prior`, `Likelihood`, `Posterior`, updater, `ProbabilityReport` | Bayesian property tests | 6 |
| RFC-0017 (missing) | DSL | `dsl` | lexer, parser, AST | golden-file parse tests | 7 |
| RFC-0020 | Compiler | `dsl.compiler` | semantic analyzer, rule validator, IR, graph builder | DC001–007 error tests | 8 |
| SPEC-04 | Decision Kernel | `decision_kernel.application` | evaluation pipeline, explainability builder | kernel determinism tests | 9 |
| SPEC-11 | Risk Engine | `risk.application` | metric calculators, scenario runner | reproducibility tests | 10 |
| SPEC-10 | Portfolio Engine | `portfolio.application` | constructor, sizing, rebalancer, validator | constraint enforcement tests | 11 |
| SPEC-12 | Behavior Engine | `behavior.application` | journaling, bias detectors, calibration tracker | deterministic scoring tests | 12 |
| SPEC-09 | Backtest | `backtest` | simulator, metrics, reports | bias-guard regression tests | 13 |
