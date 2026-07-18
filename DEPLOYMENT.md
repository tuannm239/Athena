# ATHENA — Production Deployment (Phase 5, W1)

This is the **production** deployment guide for the pilot release. It builds
on the reference wiring in `docs/DEPLOYMENT.md` (topology, scheduled jobs,
first-run bootstrap) and adds the production-grade infrastructure: multi-stage
images, an Nginx TLS edge, secret management, and dev/staging/prod separation.

> ATHENA is a **decision-support** platform. It generates Decision Objects
> only — it executes no trades and integrates no broker (see `PILOT_MODE.md`).

## Artifacts (this workstream)

| File | Purpose |
|---|---|
| `Dockerfile.production` | Multi-stage, non-root API image (venv from `uv.lock`; ships `scripts/` for pilot reports) |
| `web/Dockerfile` | Multi-stage Next.js standalone frontend image |
| `docker-compose.prod.yml` | Full production wiring; datastores unpublished, only Nginx is public |
| `nginx.conf` + `ops/nginx/proxy_common.conf` | TLS termination, security headers, edge rate-limiting, routing |
| `.env.production.example` | Environment template — copy to `.env.production` (git-ignored), never commit |
| `ops/prometheus/prometheus.prod.yml` | Production scrape + alerting config |

## Topology

```
                         :80 (ACME + redirect)
[clients] ── TLS ──▶ nginx ─┬─ / ───────▶ web:3000  (Next.js)
              :443          ├─ /api/ ────▶ api:8000  (FastAPI, N uvicorn workers)
                           └─ /health ──▶ api:8000  (public liveness only)
                                            │
                    api ─┬─▶ db:5432   (PostgreSQL 16, WAL archiving → db-backups vol)
                         ├─▶ redis:6379 (cache; password-protected, no persistence)
                         └─▶ /app/data/snapshots (DuckDB, persistent volume)

  prometheus ◀─ /metrics ─ api     alertmanager ◀─ prometheus     grafana ◀─ prometheus
  (all three: ops network only — never published to the host)
```

`/metrics`, `/health/full`, and `/pilot/status` are **blocked at the Nginx
edge** (return 404) and reachable only inside the ops network.

## Environment separation

| Env | `ATHENA_ENV` | Compose | Secrets | Notes |
|---|---|---|---|---|
| dev | `development` | `docker-compose.yml` | dev defaults OK | ports published for convenience |
| staging | `production` | `docker-compose.prod.yml` + `.env.staging` | real, staging-scoped | mirrors prod; separate DB/domain |
| prod | `production` | `docker-compose.prod.yml` + `.env.production` | real, from secret store | datastores unpublished; TLS required |

Staging and prod share the same compose file; only the `--env-file` differs.
`ATHENA_ENV=production` activates the startup secret policy (ADR-0019):
the app **refuses to boot** on the development JWT default or a secret
shorter than 32 chars.

## Secret management

- Copy `.env.production.example` → `.env.production` and fill from your secret
  store. `.env.production` and `.env.staging` are git-ignored.
- Generate secrets with `openssl rand -hex 32`.
- Provider/LLM API keys are read from the environment only
  (`ALPHAVANTAGE_API_KEY`), never hardcoded and never logged (W5 adapter).
- Rotate `JWT_SECRET` to invalidate all sessions (DR scenario S4).

## Deploy

```bash
# 0. one-time: DNS A/AAAA record for $ATHENA_DOMAIN → this host
cp .env.production.example .env.production        # then edit in real secrets

# 1. validate the compose before anything runs
docker compose -f docker-compose.prod.yml --env-file .env.production config >/dev/null

# 2. bootstrap TLS (Let's Encrypt, webroot challenge)
docker compose -f docker-compose.prod.yml --env-file .env.production up -d nginx
docker compose -f docker-compose.prod.yml --env-file .env.production run --rm certbot \
  certonly --webroot -w /var/www/certbot -d "$ATHENA_DOMAIN" \
  --cert-name athena --agree-tos -m "$LETSENCRYPT_EMAIL" --non-interactive
docker compose -f docker-compose.prod.yml --env-file .env.production restart nginx

# 3. build + start everything
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build

# 4. apply migrations (forward-only) before serving traffic
docker compose -f docker-compose.prod.yml --env-file .env.production exec api \
  alembic upgrade head

# 5. verify
curl -fsS https://$ATHENA_DOMAIN/health                     # {"status":"ok"}
docker compose -f docker-compose.prod.yml exec api \
  curl -fsS http://localhost:8000/pilot/status              # order_execution:false
```

### Behind Cloudflare
Point the orange-cloud record at the host, set SSL mode "Full (strict)", and
uncomment the `set_real_ip_from` / `real_ip_header CF-Connecting-IP` block in
`nginx.conf` so client IPs (and edge rate-limiting) are accurate.

## Migrations

Forward-only (SPEC-07). Run `alembic upgrade head` once per release **before**
the new API serves traffic. Never downgrade the schema in production — a
rollback redeploys the previous image against the newer (additive) schema.

## Rollback

```bash
# redeploy a previously built, known-good image tag
ATHENA_IMAGE_TAG=<good-sha> docker compose -f docker-compose.prod.yml \
  --env-file .env.production up -d api web
```
Migrations are additive, so the previous image runs against the current
schema. See `docs/DR_PLAN.md` for database/snapshot/secret recovery.

## Log rotation

Every service uses the `json-file` driver capped at `max-size=10m`,
`max-file=5` (50 MB/service ceiling) — set once via the `x-logging` anchor in
`docker-compose.prod.yml`. Ship stdout to your aggregator and alert on
`level=ERROR` (see `OBSERVABILITY.md`).

## Operational jobs

- **Daily pilot report** (W6): `python -m scripts.daily_report` inside the API
  container, written to the `pilot-reports` volume. Schedule via cron/systemd.
- **Backups** (W7): `pg_dump` + WAL archiving to the `db-backups` volume; see
  `docs/RUNBOOK.md` and the W7 scripts.
- **Data sync**: `ProviderSyncService` incremental sync after market close
  (`docs/DEPLOYMENT.md` §Scheduled jobs).

## Note on this environment

The Docker daemon is unavailable in the authoring environment, so images were
**not built here**; `docker compose config` validates the compose topology
statically (verified: exit 0, 9 services). Build and run steps above are to be
executed on the target host.
