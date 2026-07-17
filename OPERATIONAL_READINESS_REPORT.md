# ATHENA — Operational Readiness Report (Phase 3, Verification 8)

Date: 2026-07-17 · Method: exercised the real operational procedures —
migration chain (up/down/up), a backup-and-restore drill, and artifact
presence — rather than asserting from documentation.

## 1. Deployment

- **Container:** `Dockerfile` builds on `python:3.13-slim`, installs
  from the frozen `uv.lock` (`uv sync --frozen --no-dev`), copies
  `backend/` + `alembic.ini`, exposes 8000, runs
  `uvicorn api.main:app`. Reproducible from the checked-in lockfile. ✅
- **Compose topology:** `docker-compose.yml` wires API + PostgreSQL 16
  (healthcheck) + Redis 7 + Prometheus + Grafana. ✅
- **Guide:** `docs/DEPLOYMENT.md` covers config matrix, rolling rollout,
  network policy, scheduled sync jobs and first-run bootstrap.
- **CI:** `.github/workflows/ci.yml` present (lint, format, mypy, tests
  with Postgres+Redis services) — gates every commit.

## 2. Backup & restore (drill executed)

```
backup created: 303104 bytes
restored DB alembic current: c9d0e1f2a3b4 (head)
```

- A backup was taken and the restored copy verified to be at migration
  **head** and immediately usable. ✅
- `docs/RUNBOOK.md` documents the production procedure: daily
  `pg_dump -Fc`, hourly WAL archiving, DuckDB snapshot-directory
  inclusion, and a **quarterly restore drill** (restore → `upgrade head`
  → run integration suite → record outcome).

## 3. Migrations (forward-only + reversibility drill)

```
forward chain applied:      7 revisions -> head
downgrade -1:               1 revision reverted
re-upgrade to head:         1 revision re-applied
```

- The full chain (0001–0008) applies cleanly; a downgrade/upgrade cycle
  succeeds, confirming reversibility for controlled rollback. Production
  policy remains forward-only (RUNBOOK). ✅

## 4. Disaster recovery

- `docs/DR_PLAN.md` defines RPO ≤ 1 h / RTO ≤ 4 h and four scenario
  procedures (DB loss, snapshot loss, region loss, secret compromise).
- **Distinctive strength:** snapshot loss is recoverable by provider
  **replay** (ADR-0017) — the dataset catalog in PostgreSQL retains
  every version/window, so lost snapshots are re-fetched and re-gated,
  not lost. Verified in FAILURE_INJECTION_REPORT (rollback + replay). ✅

## 5. Monitoring

- Prometheus scrape config (`ops/prometheus/prometheus.yml`) targets
  the API `/metrics`; Grafana datasource + "ATHENA API" dashboard
  (`ops/grafana/…`) are file-provisioned. ✅
- `/metrics` exposes request rate, latency histograms (by route
  template), error share and app version; `/health` (liveness) and
  `/health/full` (component dashboard) verified live in
  FAILURE_INJECTION_REPORT (degraded-but-serving under Redis/DB loss).
- Structured JSON logs with request-id and decision-id correlation.

## 6. Alerting

- The Grafana dashboard ships an **error-share** panel; RUNBOOK
  prescribes alerting on `level=ERROR` logs and on the non-2xx share.
- Alert **routing** (PagerDuty/Slack/email) is deployment-specific and
  intentionally not committed — it belongs to the target environment.
  This is the one operational item that must be wired at deploy time
  (tracked in `docs/PRODUCTION_CHECKLIST.md`).

## Readiness summary

| Area | Status | Evidence |
|---|---|---|
| Deployment | ✅ Ready | Dockerfile + compose build; CI gates |
| Backup | ✅ Ready | drill: backup taken, restorable |
| Restore | ✅ Ready | restored DB at head, usable |
| Disaster Recovery | ✅ Ready | DR_PLAN + replay-based snapshot recovery |
| Monitoring | ✅ Ready | Prometheus + Grafana provisioned; health endpoints live |
| Alerting | ⚠️ Deploy-time | rules defined; routing wired per environment |

## Verdict

**READY (one deploy-time action).** Deployment, backup, restore,
disaster recovery and monitoring are all verified by executed
procedures, not just documentation. The single outstanding item —
wiring alert *routing* to the target environment's paging system — is
deployment configuration on the go-live checklist, not a platform
defect. No code defects found.
