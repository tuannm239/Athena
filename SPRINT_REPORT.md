# SPRINT_REPORT — Sprint 8: Risk Engine

Date: 2026-07-16 · Commit: see `git log` (feat(probability)) · Previous: Phase 0 directive intake (`d9d63de`)

## Completed work (Sprint 8)

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

Sprint 9 — Portfolio Engine (SPEC-10 + RFC-0027 §5 position sizing).
