# ATHENA — Pilot Release v1.0

**Status:** Release candidate for the human-in-the-loop production pilot
**Date:** 2026-07-18 · **Build:** API v0.4.0
**Final recommendation:** **GO WITH CONDITIONS** (conditions in §9)

ATHENA is a **Financial Decision Intelligence Platform** — a decision-support
system. This release makes it deployable to real users on real market data
while preserving the non-negotiable safety posture: **it executes no trades,
connects to no broker, generates Decision Objects only, and requires human
approval for every decision.**

---

## 1. What this release delivers (Phase 5)

| WS | Deliverable | Status |
|---|---|---|
| W1 | Production infra: `Dockerfile.production`, `web/Dockerfile`, `docker-compose.prod.yml`, `nginx.conf`, `.env.production.example`, `DEPLOYMENT.md` | ✅ |
| W2 | CI/CD release pipeline `.github/workflows/cd.yml` (lint→type→test→cov→scan→build→publish→deploy) | ✅ |
| W3 | Observability: exporters, 8 Grafana dashboards, Prometheus alerts, Alertmanager, `OBSERVABILITY.md` | ✅ |
| W4 | `SECURITY_HARDENING_REPORT.md` + CVE scanning in CI | ✅ |
| W5 | Real data provider adapter (Alpha Vantage) — closes R1 (ADR-0020) | ✅ |
| W6 | Pilot mode: flag, `/pilot/status`, daily reports, `PILOT_MODE.md` | ✅ |
| W7 | Operations: `scripts/backup.sh`, `scripts/restore.sh`, `INCIDENT_RESPONSE.md`, `docs/DR_CHECKLIST.md` | ✅ |
| W8 | `PRODUCTION_VALIDATION_REPORT.md` (all gates green) | ✅ |
| W9 | `GO_LIVE_CHECKLIST.md` | ✅ |

## 2. Deployment summary

Modular monolith behind an Nginx TLS edge. `docker-compose.prod.yml` wires 11
services: nginx, web (Next.js standalone), api (FastAPI, multi-worker
uvicorn), PostgreSQL 16, Redis 7, Prometheus, Alertmanager, Grafana, certbot,
postgres-exporter, redis-exporter. Multi-stage, **non-root** images built from
the locked dependency set. Datastores and the observability stack are
unpublished; only Nginx binds 80/443. Dev/staging/prod separated by
`--env-file`; `ATHENA_ENV=production` activates the startup secret policy.
Compose topology validated statically (`config` → exit 0). See `DEPLOYMENT.md`.

## 3. Infrastructure summary

Reproducible images from `uv.lock` / `pnpm-lock.yaml`; forward-only Alembic
migrations; persistent volumes for Postgres (with WAL archiving), DuckDB
snapshots, and pilot reports; log rotation (json-file 10m×5) on every service;
Let's Encrypt TLS with auto-renew; Cloudflare-ready real-IP block.

## 4. Security summary

Verdict **PASS** (`SECURITY_HARDENING_REPORT.md`): env-only secrets with a
production startup guard; Argon2id passwords; HS256 JWT with single-use
refresh + reuse detection; RBAC (`require_roles`); sha256-only API keys; TLS
1.2/1.3 + HSTS/CSP/security headers at the edge; layered rate limiting (app +
Nginx); non-root containers. `pip-audit` = **0 vulnerabilities** (29 prod
packages); `pnpm audit` = 2 dev/build-only advisories (accepted, tracked).
CVE scanning (pip-audit + pnpm + Trivy + CodeQL) gates every release.

## 5. Operations summary

Automated daily backups (pg_dump + snapshot tar + checksums + retention) and a
guarded restore/verification drill; incident-response playbooks by severity; a
quarterly DR checklist over the DR_PLAN scenarios; the pilot daily report
generator. Runbook, DR plan, and incident guide are cross-linked.

## 6. Monitoring summary

Native app metrics (`/metrics`, ADR-0018) + postgres/redis exporters + custom
read-only domain-state gauges (decisions, datasets, KG, features) that respect
the clean-architecture rule. 8 provisioned Grafana dashboards (System Health,
API, Decision Pipeline, Data Pipeline, Database, Redis, Knowledge Graph,
Feature Store). Prometheus alert rules → Alertmanager (pager/ops routing).
Structured JSON logs with `request_id` correlation edge→app→decision.

## 7. Known limitations

1. **Images not built in the authoring environment** (no Docker daemon);
   compose/workflows/dashboards validated statically. Build+run on the host.
2. **Frontend gates run in CI** (Node toolchain), not the authoring env.
3. **Data provider**: Alpha Vantage covers daily equity + FX; VN-native ticker
   coverage is limited (ADR-0020). Validated with a fake transport — a live
   key must be exercised at go-live.
4. **No OpenTelemetry tracing** — request-id log correlation only.
5. **Per-process rate limiter** — globally bounded by the Nginx edge zone;
   shared Redis limiter deferred (ADR-0019).

## 8. Remaining risks

| Risk | Severity | Mitigation |
|---|---|---|
| Web dev-deps CVEs (postcss/elliptic) | low | dev/build-only, not in runtime; bump when convenient |
| Live provider unverified in-env | medium | go-live condition: one real fetch + resilience check |
| Untested-on-host image build | medium | go-live condition: build/push + smoke on host |
| Alert delivery unproven | medium | go-live condition: fire a test alert end-to-end |
| Provider coverage gap (VN tickers) | medium | documented; adapter swap is a new connector, no pipeline change |

## 9. Pilot readiness assessment & final recommendation

**All engineering deliverables are complete and every automated gate is
green** (ruff, ruff format, mypy --strict: 0 issues; pytest: 365 passed / 2
skipped; coverage 95.57%). The safety posture is verified structurally: there
is no execution or broker path in the codebase, and `/pilot/status` reports
`order_execution:false` unconditionally.

What remains cannot be completed in the authoring environment — it requires the
target host and live credentials. Therefore:

### Recommendation: **GO WITH CONDITIONS**

Proceed to the pilot once these conditions are satisfied on the target host
(all are items on `GO_LIVE_CHECKLIST.md`):

1. **Build, scan, and publish** the API + web images; deploy pins the release
   tag; smoke `GET /health` over TLS.
2. **Verify the live Alpha Vantage key** with one real fetch and confirm the
   resilience wrapper behaves.
3. **Prove alerting** end-to-end: fire a test alert and confirm the page.
4. **Run the backup + restore drill** on the host (`scripts/backup.sh` then
   `scripts/restore.sh` scratch drill).
5. **Create the first ADMIN user** and confirm the human approve/reject
   workflow on a real decision.
6. **Obtain Go/No-Go sign-off** (engineering + security + product owner).

With those six conditions met, ATHENA v1.0 is cleared for the human-in-the-loop
production pilot. Feature development remains frozen; the Behavior Engine stays
advisory; the Decision Kernel remains the sole owner of business logic.

---

*Every recommendation explainable, every model backtestable, every business
rule testable. ATHENA improves decision quality; the human decides.*
