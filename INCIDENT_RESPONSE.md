# ATHENA — Incident Response Guide (Phase 5, W7)

How to respond when something breaks in the pilot. Pairs with
`docs/RUNBOOK.md` (routine ops), `docs/DR_PLAN.md` (recovery procedures),
`OBSERVABILITY.md` (signals) and `docs/DR_CHECKLIST.md` (drill checklist).

> Reminder: ATHENA executes no trades and connects to no broker. An incident
> can degrade **decision support**, never move capital. There is no
> "halt trading" action because there is no trading.

## Severity levels

| Sev | Definition | Response time | Who |
|---|---|---|---|
| **SEV-1** | API down / data loss / secret compromise | immediate | on-call + owner |
| **SEV-2** | Major degradation (high error rate, DB failover, auth broken) | < 30 min | on-call |
| **SEV-3** | Partial/again-degraded (Redis down, one endpoint failing, quarantined data) | < 4 h | ops |
| **SEV-4** | Cosmetic / informational (no-activity alert, dashboard gap) | next business day | ops |

## First 5 minutes (any alert)

1. **Acknowledge** the alert in Alertmanager (stops the page storm).
2. **Triage** with health: `GET /health` (liveness) and `GET /health/full`
   (names the failing component — degraded ≠ down).
3. **Scope**: check the System Health + API dashboards (RPS, 5xx share, p95)
   and `up{}` per target.
4. **Read logs**: `docker compose -f docker-compose.prod.yml logs --tail=200 api`
   — filter `level=ERROR`; correlate by `request_id`.
5. **Declare severity** and open an incident note (timestamp, symptom,
   suspected cause).

## Playbooks

### API down (SEV-1 / `AthenaApiDown`)
1. `docker compose -f docker-compose.prod.yml ps` — is `api` up/healthy?
2. If crash-looping, read the last logs; common causes: bad `.env.production`
   (startup secret policy refuses weak `JWT_SECRET` — check the boot error),
   DB unreachable, migration mismatch.
3. Restart: `docker compose -f docker-compose.prod.yml up -d api`.
4. If a bad release: roll back to the last good tag
   (`ATHENA_IMAGE_TAG=<good> … up -d api web`, see DEPLOYMENT.md §Rollback).

### High 5xx error rate (SEV-2 / `HighErrorRate`)
1. Which route? API dashboard error panel by `path`.
2. If one route: likely a data/dependency issue — check `/health/full`
   (database/redis/snapshots) and provider health.
3. If all routes: DB or process-wide — see "Database" below.
4. Mitigate by rolling back the last deploy if the spike aligns with it.

### Database unreachable (SEV-1/2 / `PostgresDown`)
1. `docker compose … ps db`; logs for `db`.
2. Disk full? `df -h` on the host — prune old backups/images.
3. Corruption/loss → **DR_PLAN.md S1**: provision fresh PG, restore latest
   dump (`scripts/restore.sh <dump> --target-prod --yes-i-am-sure`), replay
   WAL, `alembic upgrade head`, verify `/health/full`.

### Redis down (SEV-3 / `RedisDown`)
Cache is ephemeral (SPEC-07). The API degrades but continues. Restart redis;
it repopulates. No data recovery needed.

### Auth abuse / 429 storm (SEV-3 / `AuthAbuse`)
Sustained 429 on `/auth*` = probable credential-stuffing. Confirm in the
`security` audit trail (`audit_log` where `entity_type='security'`). The
per-host bucket + Nginx edge zone already throttle; if targeted, block the
source at the edge/Cloudflare. Rotate any credentials seen brute-forced.

### Secret compromise (SEV-1)
Follow **DR_PLAN.md S4**: rotate `JWT_SECRET` (invalidates all sessions),
revoke all API keys (`UPDATE api_keys SET revoked_at = now()`), rotate the
provider key, and review the `security` audit trail for the exposure window.

### Quarantined data (SEV-3 / `DatasetsQuarantined`)
A pipeline run failed quality gates and did **not** publish (by design).
Inspect the `datasets` table (`status='QUARANTINED'`) and the snapshot's
`quarantine` table for row-level reasons; re-fetch the bad window with
`ProviderSyncService.replay_*` (RUNBOOK).

## Escalation & communication
- SEV-1/2: notify the product owner immediately; post status in the ops
  channel every 30 min until resolved.
- Every incident gets a short write-up appended to the RUNBOOK changelog:
  timeline, root cause, fix, and a follow-up action to prevent recurrence.

## After the incident
1. Confirm all alerts cleared and dashboards nominal for 30 min.
2. Verify the latest backup is intact (`scripts/restore.sh <dump>` drill).
3. File follow-ups (blameless); update this guide if a new failure mode
   appeared.
