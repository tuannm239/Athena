#!/usr/bin/env bash
# ATHENA backup automation (Phase 5, W7).
#
# Takes a consistent daily backup of the system of record (PostgreSQL) and the
# immutable DuckDB snapshot directory, then prunes old backups by retention.
# Designed to run from cron/systemd on the production host against the compose
# stack. Idempotent; safe to re-run.
#
# Env:
#   COMPOSE_FILE   (default: docker-compose.prod.yml)
#   ENV_FILE       (default: .env.production)
#   BACKUP_DIR     (default: ./backups)
#   RETENTION_DAYS (default: 14)
#   SNAPSHOT_VOLUME name of the DuckDB snapshots volume (default: athena_snapshots)
set -euo pipefail

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
ENV_FILE="${ENV_FILE:-.env.production}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"

dc() { docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" "$@"; }

mkdir -p "$BACKUP_DIR"

echo "[backup] $STAMP — PostgreSQL (pg_dump -Fc)"
# Custom format dump (compressed, restorable with pg_restore); streamed out of
# the db container so no client tooling is needed on the host.
dc exec -T db pg_dump -U athena -Fc athena > "$BACKUP_DIR/athena-db-$STAMP.dump"

echo "[backup] $STAMP — DuckDB snapshot directory (tar.gz)"
# Snapshots are immutable files; archive the whole directory from the api
# container's mounted volume.
dc exec -T api tar -czf - -C /app/data snapshots > "$BACKUP_DIR/athena-snapshots-$STAMP.tar.gz"

echo "[backup] writing checksums"
( cd "$BACKUP_DIR" && sha256sum "athena-db-$STAMP.dump" "athena-snapshots-$STAMP.tar.gz" \
    > "athena-$STAMP.sha256" )

echo "[backup] pruning backups older than ${RETENTION_DAYS} days"
find "$BACKUP_DIR" -type f \( -name 'athena-db-*.dump' -o -name 'athena-snapshots-*.tar.gz' \
    -o -name 'athena-*.sha256' \) -mtime "+${RETENTION_DAYS}" -print -delete

echo "[backup] done -> $BACKUP_DIR (db + snapshots + checksums for $STAMP)"
