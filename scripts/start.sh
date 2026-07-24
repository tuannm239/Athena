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

# Optional in-container boot syncs (free tiers without a Shell). Both the price
# sync (SYNC_ON_START) and the company fundamentals sync (SYNC_COMPANIES_ON_START)
# each spawn a `python -m data_pipeline.cli` child that loads vnstock + pandas
# (~150–250 MB resident). On a 512 MB tier, running BOTH at once alongside
# uvicorn triples the peak and the OS OOM-kills the container mid-sync — the
# symptom is an "ATHENA_… BEGIN" line with no matching "END" and a restart.
#
# So we run them SEQUENTIALLY inside a SINGLE background orchestrator: at most
# one heavy child is resident at a time, and it never delays the port bind /
# health check (the whole block is backgrounded). Prices go first (the market
# dashboard is the primary view), companies second and batched.
(
  # ---- 1) Price sync -------------------------------------------------------
  # Default mode `ensure` (self-healing: full backfill when no readable prices,
  # else incremental top-up); set SYNC_ON_START_MODE=full to force a wider
  # backfill. SYNC_LOOKBACK_DAYS defaults to ~5 years: Athena is a decision
  # system and every publish replaces the dataset, so the snapshot must carry
  # deep daily history (probability/risk/regime/backtest need it). EOD feeds
  # return the whole window in one request per symbol, so depth is not slow.
  # Non-fatal to the API.
  if [ "${SYNC_ON_START:-false}" = "true" ]; then
    echo "===== ATHENA_SYNC BEGIN mode=${SYNC_ON_START_MODE:-ensure} ====="
    if python -m data_pipeline.cli sync "${SYNC_ON_START_MODE:-ensure}"; then
      echo "===== ATHENA_SYNC END ok (see the JSON line above for rows) ====="
    else
      echo "===== ATHENA_SYNC END FAILED (non-fatal; API keeps running) ====="
    fi
  else
    echo "[start] SYNC_ON_START is not 'true' — skipping boot price sync."
  fi

  # ---- 2) Company fundamentals sync ---------------------------------------
  # Only tickers not yet synced (--only-missing) and capped per run
  # (SYNC_COMPANIES_LIMIT, default 25) so it stays within memory and converges
  # across restarts until every universe company is populated. Runs AFTER the
  # price sync above has exited, so the two never contend for RAM.
  if [ "${SYNC_COMPANIES_ON_START:-false}" = "true" ]; then
    echo "===== ATHENA_COMPANIES BEGIN (limit=${SYNC_COMPANIES_LIMIT:-25}) ====="
    if python -m data_pipeline.cli sync companies --only-missing \
        --limit "${SYNC_COMPANIES_LIMIT:-25}"; then
      echo "===== ATHENA_COMPANIES END ok ====="
    else
      echo "===== ATHENA_COMPANIES END FAILED (non-fatal; API keeps running) ====="
    fi
  fi
) 2>&1 &

echo "[start] Launching uvicorn on 0.0.0.0:${PORT} (workers=${WEB_CONCURRENCY})…"
exec uvicorn api.main:app \
  --host 0.0.0.0 \
  --port "${PORT}" \
  --workers "${WEB_CONCURRENCY}" \
  --proxy-headers \
  --forwarded-allow-ips '*'
