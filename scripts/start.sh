#!/usr/bin/env sh
# ATHENA backend production entrypoint (Phase 3 — Render / container start).
#
# Responsibilities, in order:
#   1. Apply database migrations (forward-only, SPEC-07)  — automatic migration
#   2. Seed the initial admin if seed vars are set         — automatic seed
#   3. Exec uvicorn bound to $PORT                          — Render injects PORT
#
# `exec` on the final line hands PID 1 to uvicorn so SIGTERM reaches it
# directly: uvicorn then drains in-flight requests and shuts down
# gracefully (graceful shutdown). Migrations/seed are idempotent, so a
# restart or a scaled second instance is safe.
set -eu

PORT="${PORT:-8000}"
WEB_CONCURRENCY="${WEB_CONCURRENCY:-2}"

echo "[start] Applying database migrations (alembic upgrade head)…"
alembic upgrade head

echo "[start] Running idempotent seed…"
python -m scripts.seed

echo "[start] Launching uvicorn on 0.0.0.0:${PORT} (workers=${WEB_CONCURRENCY})…"
exec uvicorn api.main:app \
  --host 0.0.0.0 \
  --port "${PORT}" \
  --workers "${WEB_CONCURRENCY}" \
  --proxy-headers \
  --forwarded-allow-ips '*'
