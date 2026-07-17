# ATHENA Operations Runbook

## Services

`docker compose up --build` starts the API (uvicorn, port 8000), PostgreSQL 16,
Redis 7, Prometheus (9090) and Grafana (3000). Configuration via environment:
`DATABASE_URL`, `REDIS_URL`, `DUCKDB_DIR`, `JWT_SECRET` (**must** be overridden
in production — with `ATHENA_ENV=production` startup refuses the dev default),
`ACCESS_TOKEN_TTL`, `REFRESH_TOKEN_TTL`, `RATE_LIMIT_PER_MINUTE`,
`AUTH_RATE_LIMIT_PER_MINUTE`. See `docs/DEPLOYMENT.md` for the full rollout
procedure and `docs/DR_PLAN.md` for disaster recovery.

## Migrations (SPEC-07 §Migration — forward-only)

```bash
uv run alembic upgrade head      # apply
uv run alembic history           # inspect
```
Never edit an applied revision; corrections are new revisions.

## Backup & restore (SPEC-07 §Backup)

- **Daily full backup:** `pg_dump -Fc "$DATABASE_URL" > athena-$(date +%F).dump`
- **Hourly WAL archiving:** enable `archive_mode=on`,
  `archive_command='cp %p /backups/wal/%f'` on the PostgreSQL server.
- **DuckDB snapshots** (`DUCKDB_DIR`) are immutable files — include the
  directory in the daily backup; never overwrite existing snapshot files.
- **Restore drill (quarterly):** restore the latest dump into a scratch
  database, run `alembic upgrade head`, run the integration test suite
  against it, and record the outcome in this file's changelog.

## Observability

Structured JSON logs on stdout (`athena.*` loggers): every API request
carries `request_id` (echoed in the `X-Request-ID` response header); kernel
evaluations log `decision_id` for decision-trace correlation. Ship stdout to
your log aggregator; alert on `level=ERROR`.

Metrics: Prometheus scrapes `GET /metrics` (request rate, latency
histograms by route template, error share, app version). The Grafana
"ATHENA API" dashboard is provisioned from `ops/`. `GET /health/full`
reports per-component status (database, Redis, snapshots) — restrict it
and `/metrics` to the operations network.

## Incident basics

- Readiness: `GET /health` returns `{"status": "ok"}`; components via
  `GET /health/full` (degraded ≠ down — it names the failing component).
- Auth issues: verify `JWT_SECRET` consistency across replicas; check the
  `security` audit trail (`audit_log` where `entity_type='security'`)
  for login failures, refresh reuse or API-key rejections.
- 429 storms: a client exceeded the per-host bucket (`RATE_LIMIT_PER_MINUTE`
  / `AUTH_RATE_LIMIT_PER_MINUTE`); the response carries `Retry-After: 60`.
- Quality-gated data: quarantined datasets never publish — inspect the
  `datasets` table (`status = 'QUARANTINED'`) and the snapshot's
  `quarantine` table for row-level reasons. Re-fetch a bad window with
  `ProviderSyncService.replay_*` (ADR-0017); rollback a bad published
  version with `rollback_dataset` — the sync watermark rewinds with it.
