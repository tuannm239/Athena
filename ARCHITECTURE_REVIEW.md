# Architecture Review — ATHENA (v2, CTO Audit)

Date: 2026-07-15 · Supersedes the Phase-1 review (v1, commit `6eaefb4`); the
conflict register C1–C9 is retained below with current dispositions.

## 1. Principles Compliance

| Principle | Verdict | Evidence / notes |
|---|---|---|
| Clean Architecture | **Pass** | Domain has zero framework imports (grep-verified: 0 hits for fastapi/sqlalchemy/infrastructure inside `backend/*/domain`); dependency direction presentation→application→domain←infrastructure holds; application layer not yet built (planned next) |
| DDD | **Pass** | 9 bounded contexts map 1:1 to SPEC-03 (ADR-0004); aggregates enforce invariants (Decision lifecycle, Portfolio cash/allocation); ubiquitous language matches spec vocabulary |
| Hexagonal | **Pass with gap** | Repositories are ports (ABCs in domain) with SQL adapters in infrastructure; DuckDB/Redis behind adapter classes. Gap: no application-layer ports yet (unit-of-work, event publisher) — first task of the application layer |
| SOLID | **Pass** | Small single-purpose classes; interfaces segregated per context; LSP respected in `_Id` hierarchy (type-strict equality is deliberate and tested); no god objects |
| Modular monolith boundaries | **Pass** | Cross-context references are read-only published contracts (decision_kernel → risk.RiskAssessment). No context mutates another's aggregates. Import-lint automation is still manual review — recommend adding an import-linter contract in CI |
| API-first | **Pass** | OpenAPI served; full contract lands with SPEC-08 resources |
| Event model | **Gap** | Events are immutable dataclasses collected by aggregates (`pull_events`), but there is no dispatcher — RFC-0022 is missing (C1); ADR-0010 will define an interim in-process bus |
| Plugin SDK | **Not reviewable** | RFC-0021 missing (C1); SPEC-04 extension points unimplemented |
| Decision Compiler | **Not reviewable** | RFC-0020 present but RFC-0017 (DSL grammar) missing; nothing implemented yet — by design, it is sequenced after the missing RFC arrives |

## 2. Weaknesses and Recommendations

1. **No import-boundary automation.** Boundaries hold by discipline; add
   `import-linter` contracts (domain-purity, LLM-gateway isolation) to CI.
2. **Aggregate field mutability (TD6).** `Decision.invalidation_conditions`
   etc. are assignable; invariants check only at transitions. Tighten with
   intent methods when the kernel lands.
3. **No event dispatcher (RFC-0022 gap).** Until the RFC arrives, application
   services will drain `pull_events()` and publish through a port — codify in
   ADR-0010 rather than ad-hoc.
4. **Repository delete-reinsert saves (TD2).** Correct and simple; acceptable
   at current scale. Revisit if aggregates grow (positions are regenerated
   rows; audit trail preserves history).
5. **`shared_kernel.lineage` latent (TD3).** Keep; it is the reproducibility
   spine RFC-0024 requires. Wire snapshot/run ids through the pipeline sprint.
6. **Observability absent (TD1).** SPEC-00's Definition of Done demands it;
   schedule structured logging + decision-trace correlation ids no later than
   the kernel sprint, not Sprint 15.
7. **Stale CLAUDE.md (C6/D1)** remains the highest documentation risk.

## 3. Conflict Register (from v1, updated)

| # | Conflict | Status |
|---|---|---|
| C1 | RFC-0017/0021/0022 missing | **Open — blocker for DSL/Compiler/Plugin/Event modules (B-00)** |
| C2 | SPEC-03 vs SPEC-04 decision lifecycle | Resolved — ADR-0005 §1 |
| C3 | SPEC-02 Notification vs SPEC-03 Behavior context sets | Open — ADR-0012 pending ruling |
| C4 | Decision Object field sets diverge | Resolved — ADR-0005 §2 (union; compiler_version layered in Sprint 8) |
| C5 | Evidence model SPEC-03 vs RFC-0018 | **Open — must be ruled (ADR-0006) before Probability Engine** |
| C6 | CLAUDE.md stale vs canonical specs | Open — regeneration awaiting approval (B-01) |
| C7 | SPEC-02 layer-first layout vs context-first | Resolved — ADR-0001/0004 govern; annotate SPEC-02 next revision |
| C8 | Black vs ruff | Resolved — ADR-0011 |
| C9 | Three conflicting sprint numberings | Resolved — SPRINT_PLAN.md is authoritative |

## 4. Dependency Model

Package/module/runtime/event dependency graphs are maintained in
`SPRINT_PLAN.md` §1–2 and remain accurate after Sprint 2 (infrastructure
implements domain ports; no new edges). Circular dependencies: **none**
(Risk↔Portfolio dissolved at the contract level, ADR-0005 §3). Dead code:
none beyond the latent lineage module (TD3). Duplicated logic: none at
business-rule level; minor VO validation boilerplate (TD4).
