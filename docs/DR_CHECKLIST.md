# ATHENA — Disaster Recovery Checklist (Phase 5, W7)

Actionable checklist companion to `docs/DR_PLAN.md` (objectives: RPO ≤ 1 h,
RTO ≤ 4 h). Run the drill quarterly; tick every box and record the outcome in
the RUNBOOK changelog.

## Pre-req: backups are running
- [ ] `scripts/backup.sh` scheduled daily (cron/systemd) and last run succeeded
- [ ] Latest `athena-db-*.dump`, `athena-snapshots-*.tar.gz`, and `.sha256`
      present in `BACKUP_DIR`; checksums verify (`sha256sum -c`)
- [ ] PostgreSQL WAL archiving advancing (`db-backups/wal/` growing)
- [ ] Backups replicated off-host (object storage / another region)

## Restore-verification drill (quarterly)
- [ ] `scripts/restore.sh backups/athena-db-<stamp>.dump` (scratch DB) exits 0
- [ ] Drill reports non-zero `users` and `decisions` counts
- [ ] `alembic_version` matches the repo head
- [ ] Drill dropped its scratch database cleanly
- [ ] Outcome + date appended to the RUNBOOK changelog

## Scenario rehearsals (at least one per quarter)
- [ ] **S1 Database loss** — restore latest dump into fresh PG, replay WAL,
      `alembic upgrade head`, repoint API, `/health/full` → database `ok`
- [ ] **S2 Snapshot loss** — restore `snapshots.tar.gz`; for newer windows
      `ProviderSyncService.replay_*` re-fetches (quality gates re-apply)
- [ ] **S3 Full host loss** — `docker compose -f docker-compose.prod.yml up
      --build` on a new host, then S1 + S2, re-issue TLS cert, repoint DNS
- [ ] **S4 Secret compromise** — rotate `JWT_SECRET`, revoke all API keys,
      rotate provider key, review `security` audit trail

## Post-restore verification (every real recovery)
- [ ] `GET /health` → ok; `GET /health/full` all components `ok`
- [ ] `GET /pilot/status` → `order_execution:false` (posture intact)
- [ ] Smoke: register → login → create decision + evidence → probability
      review → refresh rotation → API-key round trip
- [ ] Prometheus targets all `up`; dashboards populating
- [ ] Latest pilot daily report generates (`python -m scripts.daily_report`)

## Sign-off
- [ ] Drill lead: __________  Date: __________  RTO achieved: ____  RPO: ____
