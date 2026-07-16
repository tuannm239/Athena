# ATHENA Operations Runbook

## Services

`docker compose up --build` starts the API (uvicorn, port 8000), PostgreSQL 16
and Redis 7. Configuration via environment: `DATABASE_URL`, `REDIS_URL`,
`DUCKDB_DIR`, `JWT_SECRET` (**must** be overridden in production),
`ACCESS_TOKEN_TTL`, `REFRESH_TOKEN_TTL`.

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

## Incident basics

- Readiness: `GET /health` returns `{"status": "ok"}`.
- Auth issues: verify `JWT_SECRET` consistency across replicas.
- Quality-gated data: quarantined datasets never publish — inspect the
  `datasets` table (`status = 'QUARANTINED'`) and the snapshot's
  `quarantine` table for row-level reasons.
