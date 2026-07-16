# SPRINT_REPORT — Sprint 14: Backtest Engine

Date: 2026-07-16 · Commit: see `git log` (feat(probability)) · Previous: Phase 0 directive intake (`d9d63de`)

## Completed work (Sprint 14)

- Backtest Engine (ALG-013, SPEC-09, ADR-0015): deterministic historical
  simulator with the full SPEC-09 pipeline — point-in-time universe (no
  survivorship bias), DSL-driven decisions per bar (no look-ahead: decisions
  at t earn the t→t+1 return), utility-proportional rebalancing with a
  position cap, trade recording, and the complete report (equity curve,
  drawdown curve, monthly returns, trade/decision statistics, failure
  analysis of the worst periods).
- All eleven SPEC-09 metrics: CAGR, total return, Sharpe, Sortino, Calmar,
  max drawdown, win rate, profit factor, annualized turnover, alpha and beta
  vs benchmark (OLS) — conventions codified in ADR-0015.
- 10 backtest tests incl. bit-for-bit reproducibility (SPEC-09 validation).

## Sprint 13

- Behavior Engine (ALG-014, SPEC-12, ADR-0014): confidence calibration
  (calibration error + Brier score), three deterministic detectors with
  configurable thresholds (OVERCONFIDENCE via confidence-vs-hit-rate gap,
  CONFIRMATION_BIAS via supporting-evidence share, DISPOSITION_EFFECT via
  winner/loser holding ratio), behavioral KPIs (average holding, premature
  exits, review completion), behavior score, and advisory recommendations /
  learning actions per detection (never overrides the kernel).
- Journal persistence: `JournalRepository` port + insert-only SQL
  implementation (`journal_entries`, migration 0007); the 0005
  metadata column tightened to NOT NULL via batch alter.
- 13 new behavior tests + journal round-trip integration test.

## Sprint 12

- Decision Kernel (ALG-012, SPEC-04, ADR-0013): the full 11-step pipeline —
  input/evidence validation (supporting + mandatory counter evidence,
  invalidation conditions, risk-before-return), Bayesian probability and
  confidence (RFC-0026), DSL rule adjustments applied on the posterior
  (RFC-0020 order), expected utility (RFC-0026 EU + DSL UTILITY deltas),
  ALG-007 position sizing for portfolio impact, six-facet explanation
  (why / why not / assumptions / missing information / key risks /
  alternative scenarios), and the complete Decision Object with
  matched_rules, tags, risk_adjustment and compiler_version.
- Extension seam per ADR-0013: probability and graph-execution engines are
  constructor-injected behind kernel Protocols (RFC-0021 plugins will bind
  here); kernel proven free of any LLM import path (ADR-0003 test).
- 10 kernel tests: completeness, determinism, posterior+DSL interaction,
  business-rule guards, zero-size fallback without return inputs.

## Sprint 11

- Decision Compiler back end (RFC-0020, ALG-011): immutable IR (rule id,
  version, priority, conditions, actions, tags, dependencies, source
  location), Decision Graph as a DAG with deterministic execution order
  (priority desc, rule id asc) and a Kahn cycle guard (DSL009),
  `compile_rules()` pipeline stamped with `athena-dslc/1.0.0`.
- Deterministic graph evaluator: fact-context matching (numbers, strings,
  enums, booleans, LIKE with % wildcards; missing facts never match),
  =/+=/-= action semantics with [0,1] clamping for probability and
  confidence, ordered tag union, per-rule explanations, matched/unmatched
  reporting — reproducible execution (RFC-0017 acceptance criteria).
- 12 compiler tests incl. golden ruleset outcome regression; dsl package
  coverage 98.6% (RFC gate ≥ 95%).

## Sprint 10

- RFC-0017 v2 persisted to `/rfc/0017-decision-dsl.md`; Sprint 10 unblocked.
- Decision DSL front end (ALG-010): deterministic lexer (comments, strings,
  dotted identifiers, source locations, DSL001), recursive-descent parser for
  the full v2 grammar (precedence OR<AND<NOT<parens, metadata, actions with
  =/+=/-=, TAG, EXPLAIN; DSL002/010/011/012), immutable AST per the RFC node
  list, extensible property schema over the twelve root objects (Feature ids
  registered dynamically from the Feature Store), and a semantic analyzer
  enforcing DSL003–DSL008 and DSL013–DSL015.
- Grammar note codified: IN/NOT IN/BETWEEN are not expressible with the v2
  single-literal `condition` rule and report DSL002 until a grammar revision
  adds list/range literals.
- 47 DSL tests incl. the RFC golden example; dsl package coverage 99%
  (RFC gate ≥ 95%).

## Sprint 9

- ALG-007 Position Sizing (RFC-0027 §5): `kelly_fraction` =
  max(0, p − (1−p)/b) with b = expected_return/expected_drawdown; full
  chain Kelly × RiskBudget × LiquidityFactor × Confidence × constraint cap,
  every factor validated to [0, 1].
- ALG-008 Portfolio Optimizer (SPEC-10): deterministic greedy allocator in
  descending expected-utility order (ties by ticker); enforces max position
  weight, max sector exposure, minimum cash reserve; cash never negative;
  negative-utility candidates never allocated; `PortfolioProposal` with
  allocation, cash, utility, drawdown, violations and explanation.
- 12 new unit tests: Kelly formula/clamp, sizing chain and caps, utility
  priority + determinism, cash-reserve and sector-cap enforcement,
  negative-utility exclusion.

## Sprint 8

- ALG-006 Risk Engine (RFC-0027): deterministic Decimal metric calculators —
  annualized historical volatility, historical VaR95/CVaR95 (lower-
  interpolation quantile), maximum drawdown, downside deviation, days to
  liquidate; risk score composition with directive weights and caps;
  RFC-0027 level bands VERY_LOW…CRITICAL; assessment confidence
  min(1, n/252); `build_assessment` and `build_report` (mandatory
  explanation; risk-budget violation reporting per SPEC-11 rule 2).
- 19 new unit tests: regression values on a fixed series, CVaR ≥ VaR,
  known drawdown path, zero-variance series, band boundaries, score
  boundedness/monotonicity, budget violations, determinism.

## Sprint 7

- ALG-001 Market Regime Detection (RFC-0025): `market_score` (0.30/0.20/
  0.20/0.15/0.15 weights, volatility inverted, weights renormalized over
  present inputs), `classify` (80/60/40 bands, inclusive lower bounds),
  `regime_confidence` (WeightedConsistency × DataCompleteness), and
  `evaluate_regime` producing SPEC-05 MarketContext.
- `MarketUseCases`: evaluates, persists the latest context through the
  MarketRepository port, emits `MarketRegimeChanged` only on regime change.
- Adapters: `InMemoryMarketRepository` (tests/single-process) and
  `RedisMarketRepository` (SPEC-07 short-lived market context, TTL 1 day).
- 19 new unit tests: formula, bands (parametrized boundaries), all four
  regimes reachable, missing-input and dispersion confidence effects,
  determinism, event-on-change semantics.

## Previous sprint (6)

- **Phase 0 (directive intake, `d9d63de`):** ADR-0006 evidence model applied
  end-to-end (domain, persistence, API, migration 0005); RFC-0025/0026/0027
  committed with codified deterministic formulas; `RiskLevel` re-banded per
  RFC-0027; `companies` table + repository + live `GET /companies/{ticker}`;
  `CLAUDE.md` regenerated from SPEC-00; `AGENTS.md` created.
- **Sprint 6:** Probability Engine per RFC-0026 pipeline —
  `freshness` (linear 365-day decay), `weigh` (reliability × freshness ×
  relevance), `bayesian_update` (odds-form, BF = 1+w / 1/(1+w), posterior
  provably in (0,1)), `confidence` (coverage × mean reliability ×
  consistency — separate from probability), identity calibration v1,
  `expected_utility` (ALG-005 seed), `ProbabilityReport` with mandatory
  explanation, PE001/002/003/005 error codes, and
  `ProbabilityUseCases.evaluate_decision` over stored decisions
  (prior = stored decision probability; aggregate not mutated).

## Files changed

`backend/probability/**` (new context: domain engine, report, errors,
application use case), `tests/unit/test_probability_engine.py`,
`tests/integration/test_persistence.py` (+1 class). Phase 0 touched 30+
files (see commit `d9d63de`).

## Tests & coverage

121 passed, 2 skipped (Redis — run in CI), coverage **95%** (gate ≥ 90%).
ruff + ruff format + mypy strict (138 files) green; migrations 0001–0005
verified via `alembic upgrade head`.

## RFC traceability

| Doc | Code | Tests |
|---|---|---|
| RFC-0026 §2 | `probability.domain.engine.freshness/weigh` | `TestFreshness`, `TestConfidence::test_relevance_out_of_range_is_pe002` |
| RFC-0026 §3 (RFC-0018 §5) | `bayesian_update` | `TestBayesianUpdate` (monotonicity, bounds, determinism, no-discard) |
| RFC-0026 §4 (RFC-0018 §6) | `confidence` | `TestConfidence` |
| RFC-0026 §6 | `expected_utility` | `TestExpectedUtility` |
| RFC-0018 §8/§10 | `ProbabilityReport`, PE error codes | `TestEngineReport` |
| ADR-0006 | `decision_kernel.domain.evidence` | full suite |

## Remaining work

Sprint 7 Market Regime Engine (RFC-0025) → Sprint 8 Risk Engine (RFC-0027)
→ Sprint 9 Portfolio Engine → Sprint 10–12 DSL/Compiler/Kernel
(**still blocked: RFC-0017/0021/0022 absent**) → 13 Behavior → 14 Backtest
→ 15 Scenario Simulator (**no spec**) → 16 Hardening.

## Risks

1. RFC-0017/0021/0022 remain missing — Sprints 10–12 will hit the stop
   condition unless provided.
2. Scenario Simulator (Sprint 15) has no specification.
3. PyMC (SPEC-00 ML stack) not yet introduced — current Bayesian update is
   the RFC-0026 closed-form; a PyMC-backed calibration layer can replace
   `identity-v1` without contract changes.

## Recommended next sprint

Sprint 15 — Scenario Simulator (ALG-015; SPEC-11 §Scenario Analysis):
macro/sector/liquidity shocks and portfolio stress tests, then Sprint 16
production hardening (observability, import-linter, runbooks).
