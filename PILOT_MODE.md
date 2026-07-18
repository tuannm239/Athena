# Pilot Mode (Phase 5, W6)

Pilot Mode runs ATHENA as a **decision-support system for real users on real
market data, with a human in the loop at all times.** It is an operational
posture, not a new feature — ATHENA has no trade-execution path by
construction (verified in Phase 3 Shadow Mode), so Pilot Mode *asserts and
surfaces* the guarantees rather than adding a switch that could be turned the
other way.

## Guarantees (non-negotiable)

| Property | Value | How it is guaranteed |
| --- | --- | --- |
| Read-only market access | yes | Providers implement read-only SDK ports (`PriceProvider`, `FXProvider`, …); no order/write port exists. |
| Order execution | **disabled** | No execution adapter exists anywhere in the codebase. |
| Broker integration | **none** | No broker client, credentials, or import path. |
| Human approval | **mandatory** | A Decision is `DRAFT → UNDER_REVIEW → APPROVED / REJECTED`; only a human transition approves it (`decision_kernel.domain.decision`). |
| Audit trail | **full** | Every decision write emits an insert-only `AuditRow` (SPEC-07). |
| Decision history | **retained** | Decisions and their `review_history` persist in the system of record. |
| Daily reports | **generated** | `scripts/daily_report.py` (see below). |

ATHENA generates **Decision Objects only**. It never allocates capital.

## Enabling

Set one environment variable (see `.env.production.example`):

```bash
ATHENA_PILOT_MODE=true      # accepts 1 / true / yes (case-insensitive)
```

The flag is read by `Settings.from_env()` and surfaced to operators at:

- `GET /health/full` → includes `"pilot_mode": true`
- `GET /pilot/status` → the full posture object:

```json
{
  "pilot_mode": true,
  "environment": "production",
  "read_only_market_access": true,
  "order_execution": false,
  "broker_integration": false,
  "human_approval_required": true,
  "audit_trail": true
}
```

The flag changes **no business logic**. `order_execution` is reported `false`
whether the flag is on or off, because there is no execution path either way.

## Daily reports

The retained daily record is produced by an operational, **read-only**
(SELECT-only) script:

```bash
# defaults to today (UTC); pass a date to backfill
python -m scripts.daily_report [YYYY-MM-DD]

# where reports are written (default: data/pilot-reports/)
export ATHENA_PILOT_REPORT_DIR=/var/athena/pilot-reports
```

It writes `pilot-report-<date>.json` and `pilot-report-<date>.md` containing:

- decisions created that day, broken down by status;
- human review activity that day (approvals / rejections, derived from audit
  `UPDATE` events whose snapshot status is `APPROVED` / `REJECTED`);
- lifetime decisions by status (portfolio-wide posture);
- all audit events that day (`entity_type:action` counts).

Schedule it once per day (cron / systemd timer / CI schedule) against the
production database, e.g.:

```cron
15 0 * * *  cd /opt/athena && DATABASE_URL=... python -m scripts.daily_report
```

The script only reads; it never mutates state and holds no business logic.
