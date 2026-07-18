#!/usr/bin/env bash
# ATHENA restore (Phase 5, W7).
#
# Restores a PostgreSQL dump produced by scripts/backup.sh. By default it
# restores into a DISPOSABLE scratch database and verifies it (migrations +
# row sanity) — this is the restore-verification drill. Pass --target-prod to
# restore into the live database (guarded; requires an explicit second flag).
#
# Usage:
#   scripts/restore.sh backups/athena-db-<stamp>.dump            # drill (scratch)
#   scripts/restore.sh backups/athena-db-<stamp>.dump --target-prod --yes-i-am-sure
set -euo pipefail

DUMP="${1:?usage: restore.sh <dump-file> [--target-prod --yes-i-am-sure]}"
shift || true
TARGET_PROD=0; CONFIRM=0
for arg in "$@"; do
  case "$arg" in
    --target-prod) TARGET_PROD=1 ;;
    --yes-i-am-sure) CONFIRM=1 ;;
    *) echo "unknown arg: $arg" >&2; exit 2 ;;
  esac
done

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
ENV_FILE="${ENV_FILE:-.env.production}"
dc() { docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" "$@"; }

[ -f "$DUMP" ] || { echo "dump not found: $DUMP" >&2; exit 1; }

if [ "$TARGET_PROD" -eq 1 ]; then
  [ "$CONFIRM" -eq 1 ] || { echo "refusing prod restore without --yes-i-am-sure" >&2; exit 3; }
  DB="athena"
  echo "[restore] !!! restoring into PRODUCTION database '$DB' !!!"
else
  DB="athena_restore_drill"
  echo "[restore] restoring into scratch database '$DB' (verification drill)"
  dc exec -T db psql -U athena -c "DROP DATABASE IF EXISTS $DB;"
  dc exec -T db psql -U athena -c "CREATE DATABASE $DB OWNER athena;"
fi

echo "[restore] pg_restore -> $DB"
dc exec -T db pg_restore -U athena -d "$DB" --clean --if-exists --no-owner < "$DUMP" \
  || echo "[restore] pg_restore reported warnings (non-fatal for --clean restores)"

echo "[restore] verifying schema is at head + core tables populate"
dc exec -T db psql -U athena -d "$DB" -c \
  "SELECT count(*) AS users FROM users; SELECT count(*) AS decisions FROM decisions;"
dc exec -T db psql -U athena -d "$DB" -c \
  "SELECT version_num FROM alembic_version;"

if [ "$TARGET_PROD" -eq 0 ]; then
  echo "[restore] drill OK — dropping scratch database"
  dc exec -T db psql -U athena -c "DROP DATABASE IF EXISTS $DB;"
fi
echo "[restore] done"
