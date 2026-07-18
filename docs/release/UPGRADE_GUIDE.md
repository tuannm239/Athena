# Athena — Upgrade Guide

How to move an existing deployment to v1.0, and general upgrade practice.

## v1.0 is compatible

Phase 6 is **additive and frontend-focused**. There are **no breaking API
changes**, no schema-breaking migrations, and no configuration removals.
Existing clients and integrations keep working unchanged.

## Upgrade steps

```bash
# 1. Fetch the release
git fetch --tags && git checkout v1.0        # or pull the release images

# 2. Apply migrations (forward-only; no-op if already current)
docker compose -f docker-compose.prod.yml --env-file .env.production \
  exec api alembic upgrade head

# 3. Roll the API + web images
ATHENA_IMAGE_TAG=1.0 docker compose -f docker-compose.prod.yml \
  --env-file .env.production up -d api web

# 4. Verify
curl -fsS https://$ATHENA_DOMAIN/health           # {"status":"ok"}
```

No new **required** environment variables were introduced in v1.0. Optional
pilot/report settings are documented in `.env.production.example` and
`PILOT_MODE.md`.

## Client-side state

The web app stores UX preferences, favorites, recent items, saved filters and
notification read-state in the browser's `localStorage` under `athena-ux` and
`athena-notifications`. These are versioned; v1.0 introduces version 1 and
requires no migration. Clearing site data resets them harmlessly.

## Rollback

```bash
ATHENA_IMAGE_TAG=<previous-good> docker compose -f docker-compose.prod.yml \
  --env-file .env.production up -d api web
```

Migrations are additive/forward-only — the previous image runs against the
current schema. See `docs/DR_PLAN.md` for recovery scenarios.

## General practice

- Always run `docker compose ... config` before deploying.
- Pin `ATHENA_IMAGE_TAG` to the release SHA/tag; never deploy `latest` blind.
- Take a backup first (`scripts/backup.sh`) and keep the previous tag reachable.
