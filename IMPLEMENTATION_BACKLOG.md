# IMPLEMENTATION_BACKLOG — ATHENA

Sorted by dependency order. Detailed sub-tasks for Sprints 2–6 live in
`TASK_PLAN.md` (S2–S6 IDs, all fields); this backlog consolidates every
remaining unit of work. Complexity: S ≤ 2h, M ≤ 4h, L ≤ 1 day, XL = split
before starting. Priority: P0 blocker-critical … P3 nice-to-have.

| ID | Title | Description | Deps | Cx | Pri | Refs | Acceptance criteria |
|---|---|---|---|---|---|---|---|
| B-00 | Obtain RFC-0017/0021/0022 | Author or upload Decision DSL, Plugin SDK, Event Model RFCs | user | — | **P0** | C1 | documents merged to /rfc |
| B-01 | Regenerate CLAUDE.md from SPEC-00 | Remove draft-era pipeline/override; point at canonical specs | user approval | S | **P0** | C6, D1 | CLAUDE.md matches SPEC-00; no override stage |
| B-02 | AGENTS.md | Session operating guide pointing at constitution, plans, gates | B-01 | S | P1 | D2 | file exists, referenced docs valid |
| B-03 | Application layer scaffolding | Use-case base, unit-of-work port, event publisher port | — | M | P0 | SPEC-02 layers | app layer imports domain only |
| B-04 | Response envelope + error mapper | request_id/timestamp/status/data/errors; DomainError→422 map | B-03 | M | P0 | SPEC-08, TASK S3-02/03 | all endpoints wrapped; error codes tested |
| B-05 | AuthN/AuthZ | ADR-0009; register/login, JWT issue/verify/refresh, role guard | B-03 | L | P0 | SPEC-08, S3-01/04 | 401/403 paths tested |
| B-06 | Decisions REST resource | GET list/id, POST, PATCH over app services | B-04, Sprint2 | L | P0 | SPEC-08, S3-05 | endpoints match spec, integration-tested |
| B-07 | Portfolios REST resource | GET list/id/positions, POST | B-04 | M | P0 | SPEC-08, S3-06 | pagination + tests |
| B-08 | Companies persistence ruling + resource | resolve F17, implement CompanyRepository impl + GET endpoints | B-04, ruling | M | P1 | SPEC-07/08, F17 | round-trip + endpoint tests |
| B-09 | Market context endpoints | /market/context /market/regime /market/sectors (501 until ALG-001) | B-04 | S | P1 | SPEC-08 | paths exist, contract documented |
| B-10 | OpenAPI artifact in CI | commit openapi/v1.json, diff-check | B-06..09 | S | P1 | SPEC-08, S3-08 | CI fails on drift |
| B-11 | Feature Store core | registry, metadata, lifecycle, read APIs | B-03 | L | P0 | RFC-0023, S4-01..03 | published features immutable |
| B-12 | Factor Library | factor metadata + registration validation + SPEC-06 catalogue defs | B-11 | L | P1 | SPEC-06, S4-08/09 | registration gates enforced |
| B-13 | Data Pipeline framework | stages, quarantine, versioning, lineage, quality reports, public ops | B-11 | L | P0 | RFC-0024, S4-04..07 | failed datasets never publish |
| B-14 | Knowledge Graph | ADR-0007; nodes/edges, versioned mutations, traversals, explain | B-13 | L | P1 | RFC-0019, S5-01..05 | deterministic traversal tests |
| B-15 | Evidence model ruling | ADR-0006 unify SPEC-03 vs RFC-0018 evidence | user ruling | S | **P0** | C5, R3 | ADR accepted, domain updated once |
| B-16 | ALG-001 Market Regime Detection | deterministic regime + confidence from indicator inputs | B-11 | L | P0 | SPEC-05 | 4 regimes, reproducible, >90% cov |
| B-17 | ALG-002 Factor Engine | quality/growth/value/momentum/liquidity/risk calculators | B-12, B-13 | XL→split | P1 | SPEC-06 | deterministic, benchmarked |
| B-18 | ALG-004 Probability Engine | prior→likelihood→posterior→confidence; PE error codes | B-15 | L | P0 | RFC-0018, S6-02..06 | same input ⇒ same output; property tests |
| B-19 | ALG-005 Expected Utility | posterior+risk+return+impact → utility | B-18 | M | P0 | RFC-0018 §7 | unit-tested, deterministic |
| B-20 | ALG-006 Risk Engine | vol, VaR, CVaR, max drawdown, tail, liquidity; levels+confidence | B-13 | L | P0 | SPEC-11 | reproducible metrics, regression suite |
| B-21 | ALG-007 Position Sizing | risk budget, limits, cash constraint → allocation | B-20 | L | P0 | SPEC-10 | constraints never violated in tests |
| B-22 | ALG-008 Portfolio Optimizer | maximize utility s.t. constraints; proposal + explanation | B-21, B-19 | L | P0 | SPEC-10 | utility non-decreasing; violations reported |
| B-23 | ALG-010/011 DSL + Compiler | lexer→parser→AST→semantic→IR→graph→object; DC error codes | **B-00** | XL→split | P0 | RFC-0017*, RFC-0020 | golden files; 100% stage coverage |
| B-24 | ALG-012 Decision Kernel | SPEC-04 pipeline; explanation six-fields; decision types | B-18..B-22 (+B-23 for DSL path) | XL→split | P0 | SPEC-04 | deterministic; kernel has no LLM import path |
| B-25 | Event dispatch | in-process bus per RFC-0022 (ADR-0010 interim if missing) | B-03 | M | P1 | RFC-0022*, SPEC-03 | events published by app layer only |
| B-26 | ALG-013 Backtest Engine | simulation modes, bias guards, metrics, reports, benchmarks | B-24 | XL→split | P1 | SPEC-09 | reproducible; VNINDEX/VN30 benchmark hooks |
| B-27 | ALG-014 Behavior Engine | bias detectors, journal service, calibration, KPIs | B-24 | L | P1 | SPEC-12 | deterministic scoring |
| B-28 | ALG-015 Scenario Simulator | needs spec first (F13) | spec | L | P2 | SPEC-01 | spec exists, then per spec |
| B-29 | LLM Gateway | single import point, lineage tagging, explanation validation | B-24 | M | P2 | SPEC-00, ADR-0003 | import-lint proves kernel isolation |
| B-30 | Research Copilot | summaries over gateway | B-29 | M | P2 | SPEC-01 | sources mandatory |
| B-31 | Observability | structured logging, decision-trace correlation ids, metrics | any | M | P1 | SPEC-00 DoD, TD1 | every decision traceable in logs |
| B-32 | Integration hardening | e2e decision flow, perf profile, backup runbook, security pass | B-24.. | XL→split | P1 | Sprints 13–15 | SPRINT_PLAN §13–15 gates |
