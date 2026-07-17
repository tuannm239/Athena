# ATHENA — Deployment Guide (Phase 2, Module 9)

## Topology

Modular monolith (ADR-0001): one API container plus PostgreSQL 16,
Redis 7, and (optional but recommended) Prometheus + Grafana. All five
are described in `docker-compose.yml`; any container platform works —
the compose file is the reference wiring.

```
[clients] → TLS proxy → api:8000 → postgres:5432
                              ↘ → redis:6379
        prometheus ← /metrics ↲     duckdb dir (volume)
        grafana ← prometheus
```

## Configuration (environment variables)

| Variable | Required in prod | Notes |
|---|---|---|
| `ATHENA_ENV` | yes → `production` | enables the startup secret policy |
| `JWT_SECRET` | yes | ≥ 32 chars; startup refuses the dev default |
| `DATABASE_URL` | yes | `postgresql+psycopg://…` |
| `REDIS_URL` | yes | ephemeral cache only |
| `DUCKDB_DIR` | yes | persistent volume; immutable snapshots |
| `ACCESS_TOKEN_TTL` / `REFRESH_TOKEN_TTL` | no | defaults 900 / 1209600 s |
| `RATE_LIMIT_PER_MINUTE` / `AUTH_RATE_LIMIT_PER_MINUTE` | no | defaults 240 / 20 per host |

Provider and LLM API keys are constructor-injected at the composition
root; keep them in the platform secret store, never in images.

## Rollout procedure

1. Build: `docker build -t athena-api:<sha> .` (or `docker compose build`).
2. Migrate: `uv run alembic upgrade head` (forward-only; run once per
   release, before the new API starts).
3. Start/replace the API container; startup is ~50 ms (BENCHMARKS), so
   rolling replacement causes no visible gap behind a proxy.
4. Verify: `GET /health` is `ok`; `GET /health/full` shows every
   component `ok`; `/metrics` scrapes.
5. Rollback = redeploy the previous image. Migrations are additive
   (forward-only); do not downgrade the schema in production —
   previous images run against the newer schema.

## Network policy (required in production)

- Terminate TLS in front of the API; the app serves plain HTTP.
- Expose **only** `/api/v1/*` and `/health` publicly. Restrict
  `/metrics`, `/health/full`, Prometheus (9090) and Grafana (3000) to
  the operations network (SECURITY_REVIEW A05).

## Scheduled jobs

Daily after market close (cron/systemd timer, single instance):
1. `ProviderSyncService.incremental_sync_prices(...)` and
   `incremental_sync_macro(...)` — watermark-driven, idempotent, no-op
   when nothing is new (ADR-0017).
2. `KnowledgeSyncService.sync_companies(...)` — idempotent.
3. `pg_dump` daily backup + snapshot-directory sync (RUNBOOK).

## First-run bootstrap

1. `alembic upgrade head`.
2. Register the first user via `POST /api/v1/auth/register` (ANALYST).
3. Role elevation to ADMIN is an operator action for now (ADR-0019):
   `UPDATE users SET role = 'ADMIN' WHERE email = …`.
4. Full sync to seed data: `full_sync_prices` over the initial window,
   then verify `GET /health/full` and the published dataset in the
   `datasets` table.
