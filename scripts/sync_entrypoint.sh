#!/usr/bin/env sh
# Docker / cron entrypoint for scheduled market synchronisation.
#
# Cron-compatible: one-shot, deterministic exit code. Point a scheduler
# (Render Cron Job, k8s CronJob, or crontab) at this script. The action is
# chosen by SYNC_MODE so the same image serves every schedule.
set -eu
MODE="$(printf '%s' "${SYNC_MODE:-INCREMENTAL}" | tr '[:lower:]' '[:upper:]')"
echo "[sync] SYNC_MODE=${MODE} tickers=${SYNC_TICKERS:-<default>}"
case "${MODE}" in
  FULL)         exec python -m data_pipeline.cli sync full ;;
  INCREMENTAL)  exec python -m data_pipeline.cli sync incremental ;;
  MANUAL)       echo "[sync] MANUAL — no scheduled run; invoke 'athena sync ...' by hand." ; exit 0 ;;
  *)            echo "[sync] ERROR: unknown SYNC_MODE='${MODE}' (FULL|INCREMENTAL|MANUAL)" ; exit 2 ;;
esac
