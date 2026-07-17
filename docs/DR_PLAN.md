# ATHENA — Disaster Recovery Plan (Phase 2, Module 9)

## Objectives

| Metric | Target | Basis |
|---|---|---|
| RPO (data loss tolerance) | ≤ 1 hour | hourly WAL archiving (SPEC-07 §Backup) |
| RTO (service restoration) | ≤ 4 hours | single-region restore procedure below |

## State inventory (what must survive)

1. **PostgreSQL** — system of record: users/credentials/API keys,
   decisions + evidence, portfolios, KG nodes/edges (versioned),
   feature registry, dataset catalog, journal, audit trail.
2. **DuckDB snapshot directory** (`DUCKDB_DIR`) — immutable dataset
   snapshots (published + quarantined). Loss is recoverable by
   provider **replay** (ADR-0017): re-fetch the affected windows; the
   catalog in PostgreSQL still knows every version and window end date.
3. **Redis** — ephemeral by design (SPEC-07): market-context cache
   only. No recovery needed; it repopulates.
4. **Secrets** — `JWT_SECRET`, provider/LLM API keys: live in the
   deployment secret store, never in backups. Rotating `JWT_SECRET`
   invalidates all sessions (users re-login) — acceptable in DR.

## Scenarios & procedures

### S1 — Database loss/corruption
1. Provision a fresh PostgreSQL 16 instance.
2. Restore latest daily dump: `pg_restore -d "$DATABASE_URL" latest.dump`.
3. Replay WAL to the failure point (RPO ≤ 1 h).
4. `uv run alembic upgrade head` (no-op if the dump is current; safe —
   forward-only).
5. Run the integration suite against the restored DB, then repoint the
   API and verify `GET /health/full` → database `ok`.

### S2 — Snapshot directory loss
1. Restore `DUCKDB_DIR` from the daily backup if available.
2. For windows newer than the backup: `ProviderSyncService.replay_*`
   over the missing windows (versions from the `datasets` table).
   Quality gates re-apply automatically; lineage marks the re-fetch.

### S3 — Full region/host loss
1. Rebuild from the repository: `docker compose up --build` on the new
   host (images are reproducible from the checked-in Dockerfile).
2. Apply S1 then S2. Point DNS at the new host.
3. Re-create Prometheus/Grafana from `ops/` provisioning (stateless
   dashboards; Grafana volume is convenience only).

### S4 — Secret compromise
1. Rotate `JWT_SECRET` → all access/refresh tokens die immediately
   (refresh jtis in the DB become irrelevant; access tokens fail
   signature checks).
2. Revoke all API keys (`UPDATE api_keys SET revoked_at = now()`),
   notify owners, re-issue.
3. Review the `security` audit trail for the exposure window.

## Verification cadence

- **Quarterly restore drill** (RUNBOOK): restore latest dump to a
  scratch database, `alembic upgrade head`, run the integration suite,
  record the outcome.
- **Monthly**: verify WAL archiving is advancing and the snapshot
  backup includes the newest published versions.
- Every drill outcome is appended to the RUNBOOK changelog.
