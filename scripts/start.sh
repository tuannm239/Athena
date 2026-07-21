#!/usr/bin/env sh
# ATHENA backend production entrypoint (Phase 3 — Render / container start).
#
# Responsibilities, in order:
#   1. Apply database migrations (forward-only, SPEC-07)  — automatic migration
#   2. Seed the initial admin if seed vars are set         — automatic seed
#   3. Optionally kick a background market sync            — SYNC_ON_START
#   4. Exec uvicorn bound to $PORT                          — Render injects PORT
#
# `exec` on the final line hands PID 1 to uvicorn so SIGTERM reaches it
# directly: uvicorn then drains in-flight requests and shuts down
# gracefully (graceful shutdown). Migrations/seed are idempotent, so a
# restart or a scaled second instance is safe.
set -eu

PORT="${PORT:-8000}"
WEB_CONCURRENCY="${WEB_CONCURRENCY:-2}"

echo "[start] Applying database migrations (alembic upgrade head)…"
# Invoke via `python -m` (not the bare `alembic` console script) so it never
# depends on the venv's scripts being on PATH — only on the venv python, which
# runs this whole entrypoint.
python -m alembic upgrade head

echo "[start] Running idempotent seed…"
python -m scripts.seed

# Optional provider diagnostic (free tiers without a Shell): when
# PROVIDER_TEST_ON_START=true, probe every supported vnstock source once and
# print the JSON report to the logs. This is how you run `athena provider test`
# on a plan with no Shell — set the flag, redeploy, and read the result in the
# logs (it reveals whether this server can actually reach the VN data source).
# Runs in the BACKGROUND so it never delays the port bind / health check.
if [ "${PROVIDER_TEST_ON_START:-false}" = "true" ]; then
  echo "[start] PROVIDER_TEST_ON_START=true — probing vnstock sources (see JSON below)…"
  (
    python -m data_pipeline.cli provider test \
      || echo "[start] provider test reported the configured source is unreachable (see JSON above)"
  ) &
fi

# Optional in-container market sync (free tiers without a Shell): when
# SYNC_ON_START=true, run one sync in the BACKGROUND so it never delays the
# port bind / health check. It writes to the same filesystem the API reads, so
# the dashboard populates a short while after boot. Default mode is
# `ensure` (self-healing: full backfill when no readable prices, else
# incremental top-up); set SYNC_ON_START_MODE=full to force a wider backfill. Keep
# SYNC_LOOKBACK_DAYS small (e.g. 10) so a fresh ephemeral disk syncs quickly —
# the snapshot only needs the latest closes. Failure is non-fatal to the API.
if [ "${SYNC_ON_START:-false}" = "true" ]; then
  echo "[start] SYNC_ON_START=true — launching '${SYNC_ON_START_MODE:-incremental}' market sync in background…"
  (
    echo "===== ATHENA_SYNC BEGIN mode=${SYNC_ON_START_MODE:-ensure} ====="
    if python -m data_pipeline.cli sync "${SYNC_ON_START_MODE:-ensure}"; then
      echo "===== ATHENA_SYNC END ok (see the JSON line above for rows) ====="
    else
      echo "===== ATHENA_SYNC END FAILED (non-fatal; API keeps running) ====="
    fi
  ) 2>&1 &
else
  echo "[start] SYNC_ON_START is not 'true' — skipping boot sync (dashboard will be empty until a sync runs)."
fi

echo "[start] Launching uvicorn on 0.0.0.0:${PORT} (workers=${WEB_CONCURRENCY})…"
exec uvicorn api.main:app \
  --host 0.0.0.0 \
  --port "${PORT}" \
  --workers "${WEB_CONCURRENCY}" \
  --proxy-headers \
  --forwarded-allow-ips '*'
