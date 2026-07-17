# ATHENA — Production Readiness Report

Date: 2026-07-16 · Scope: backend platform after Phase 2 (Production
Integration, Modules 1–9) · Basis: 218 source files, 338 tests
(2 Redis tests run in CI only), coverage 96 % (gate ≥ 90 %), mypy
--strict clean, ruff lint+format clean, migrations 0001–0008 verified
end-to-end, CI green on every module commit.

---

## 1. Architecture compliance

| Constitution rule | Enforcement | Status |
|---|---|---|
| Domain layer framework-free | `test_architecture.py::test_domain_layer_is_framework_free` | ✅ machine-enforced |
| No SQL outside infrastructure | `test_no_sql_in_domain_or_application` | ✅ machine-enforced |
| Application never imports infrastructure | `test_application_layer_does_not_import_infrastructure` | ✅ machine-enforced |
| LLM isolation (ADR-0003), both directions | guarded contexts (now incl. dsl/probability/market/backtest) cannot import `llm_gateway`; the gateway cannot import them | ✅ machine-enforced |
| Money/probability are Decimal, never float | value objects + connector string-encoding convention (ADR-0017) | ✅ |
| Every recommendation explainable | six-facet `KernelExplanation`; KG provenance; LLM lineage tags | ✅ |
| Behavioral feedback advisory only | Behavior Engine has no kernel write path | ✅ |
| Provider replaceability | ten SDK Protocols + configuration-driven registry; adapters independently tested | ✅ |

Bounded contexts map 1:1 to packages (ADR-0004); 19 accepted ADRs
(index `adr/README.md`); every module has a `TRACEABILITY_MATRIX.md`
row.

## 2. Security compliance

Controls landed in Module 7 (ADR-0019), all integration-tested:
RBAC (VIEWER/ANALYST/ADMIN, per-request checks, 403 mapping); API keys
(sha256-only storage, shown once, revocable, X-API-Key auth);
single-use refresh tokens with reuse detection; production startup
policy refusing dev/short JWT secrets; per-host rate limiting with a
strict auth bucket (429 + Retry-After); insert-only security audit
trail. OWASP Top 10 assessment: `docs/SECURITY_REVIEW.md` — A01–A04,
A07–A09 mitigated; A05/A06/A10 partial with prioritized follow-ups
(CVE scanning in CI, ops-endpoint network policy, shared rate limiter,
password reset pending a notification channel).

## 3. Performance benchmarks

Baseline `docs/BENCHMARKS.md` (Module 8); every target met with ≥10×
headroom: kernel graph evaluation 0.052 ms P95 (~28 k ops/s), ruleset
compile 2.1 ms P95, probability update (30 evidence) 1.2 ms P95, KG
queries 0.13 ms P95 at 1 k nodes, one-year × 20-ticker backtest 64 ms,
cold startup 46 ms. Watchpoints: KG at ≥100 k nodes; backtest
vectorization for intraday data.

## 4. Operational readiness

- **Deployment:** `docs/DEPLOYMENT.md` (compose reference topology,
  config matrix, rolling rollout, network policy, scheduled sync jobs).
- **Runbook:** `docs/RUNBOOK.md` (migrations, backup/WAL, observability,
  incidents incl. quarantine/replay/rollback procedures).
- **DR:** `docs/DR_PLAN.md` — RPO ≤ 1 h / RTO ≤ 4 h, four scenario
  procedures; snapshot loss is additionally recoverable by provider
  replay (ADR-0017). Quarterly restore drill defined.
- **Checklist:** `docs/PRODUCTION_CHECKLIST.md` for go-live.
- **Observability:** Prometheus metrics + provisioned Grafana dashboard,
  `/health` + `/health/full`, structured logs with request/decision
  correlation ids.
- **Data operations:** quality-gated, lineage-tagged, idempotent
  incremental sync with watermark recovery; quarantine never publishes.

## 5. Known risks

| # | Risk | Severity | Mitigation |
|---|---|---|---|
| R1 | No real market-data vendor connector yet (Static/LocalFile only) | **High for live use** | SDK + resilience layer ready; writing a vendor adapter is adapters-only work (Module 2 pattern) |
| R2 | Rate limiting is per-process | Medium | single-replica deployments unaffected; Redis limiter planned before horizontal scaling |
| R3 | RFC-0021 (plugin SDK) / RFC-0022 (event model) unspecified | Medium | seams exist (kernel ports ADR-0013, in-process bus ADR-0010); no blocker for current scope |
| R4 | Role administration is an ops action (no admin API) | Low | documented (ADR-0019/DEPLOYMENT); small surface |
| R5 | No CVE scanning in CI | Medium | add pip-audit/Dependabot (SECURITY_REVIEW follow-up #1) |
| R6 | Calibration uses identity-v1 (PyMC model pending) | Low | probabilities remain Bayesian and explainable; calibration is additive |

## 6. Remaining technical debt

1. Market/factor endpoints return 501 until a real data feed lands
   (contract is fully specified and tested).
2. Frontend (Next.js) not started — API-first surface is complete.
3. Notification context undecided (C3 → planned ADR-0012).
4. OpenTelemetry tracing deferred by decision (ADR-0018) until a second
   service exists.
5. Feature Store storage ADR-0008 write-up pending (implementation
   exists and is tested).

## 7. Deployment recommendation

Deploy as a **single-replica modular monolith** behind TLS with the
ops endpoints network-restricted, following `docs/DEPLOYMENT.md` and
gating go-live on `docs/PRODUCTION_CHECKLIST.md`. Schedule the daily
incremental sync + backup jobs from day one. Do not scale horizontally
before the shared rate limiter (R2).

## 8. Go/No-Go decision

**GO — conditional.** The backend platform is production-ready as a
decision-intelligence service for an internal analyst pilot: every
architectural guarantee is machine-enforced, security controls are
tested, performance has an order-of-magnitude headroom, and operations
(deploy/backup/DR/monitoring) are documented and reproducible.

Conditions before broad production use:
1. **Provision a real market-data provider adapter** (R1) — the single
   material gap between pilot and production; everything downstream of
   the provider SDK is already quality-gated and tested.
2. Complete the go-live checklist in the target environment, including
   one restore drill (DR_PLAN).
3. Land CVE scanning in CI (R5).

No-Go applies only to unattended/automated capital allocation — which
the platform **by constitution does not do**: ATHENA improves decision
quality; humans approve decisions (SPEC-00, enforced by the Decision
aggregate's review lifecycle).
