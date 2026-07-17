# ATHENA — Production Go-Live Checklist (Phase 2, Module 9)

Tick every box before exposing the platform to real users.

## Configuration & secrets
- [ ] `ATHENA_ENV=production` set (startup secret policy active)
- [ ] `JWT_SECRET` ≥ 32 random chars from the secret store (never the dev default — startup enforces)
- [ ] Provider / LLM API keys in the secret store; absent from images, logs and repo
- [ ] Token TTLs and rate limits reviewed for the audience

## Data layer
- [ ] `alembic upgrade head` applied (0001–0008); `alembic history` matches the repo
- [ ] `DUCKDB_DIR` on a persistent, backed-up volume
- [ ] Daily `pg_dump` + hourly WAL archiving scheduled (RUNBOOK)
- [ ] Restore drill executed once against this environment (DR_PLAN)

## Security
- [ ] TLS termination in front of the API
- [ ] `/metrics`, `/health/full`, Prometheus, Grafana restricted to the ops network
- [ ] First ADMIN user created; role policy understood (ADR-0019)
- [ ] Grafana default admin password changed
- [ ] SECURITY_REVIEW follow-ups triaged (CVE scanning, shared rate limiter)

## Observability
- [ ] Prometheus scraping `athena-api` (target up)
- [ ] Grafana ATHENA API dashboard loading; error-share panel alerting wired
- [ ] Logs shipped from stdout; alert on `level=ERROR`
- [ ] `GET /health/full` all components `ok`

## Data operations
- [ ] Daily incremental sync job scheduled (prices, macro) — single instance
- [ ] KG company/sector sync scheduled
- [ ] Quarantine monitoring: alert when a sync run lands `QUARANTINED`

## Verification
- [ ] CI green on the deployed commit (lint, format, mypy --strict, tests ≥ 90% coverage)
- [ ] `scripts/benchmark.py` run on production-class hardware; results within 2× of docs/BENCHMARKS.md
- [ ] Smoke: register → login → create decision with evidence → probability review → refresh rotation → API-key round trip
