# Athena — Administrator Guide

For operators who deploy and run Athena. This covers accounts, roles, and the
day-to-day admin surface. For infrastructure and operations, see
`DEPLOYMENT.md`, `OBSERVABILITY.md`, `INCIDENT_RESPONSE.md`, and
`docs/RUNBOOK.md` at the repository root.

## Roles (RBAC — ADR-0019)

| Role | Can |
|---|---|
| `VIEWER` | read dashboards, decisions, portfolios, reports |
| `ANALYST` | the above **+** create/update decisions and add evidence, run reviews |
| `ADMIN` | the above **+** administration screen and user/role management |

Roles are enforced **server-side** on every request — the frontend only hides
controls a role cannot use. Write routes require ANALYST or ADMIN.

## First run

1. Deploy per `DEPLOYMENT.md` and apply migrations (`alembic upgrade head`).
2. Register the first user via `POST /api/v1/auth/register` (created as
   `ANALYST`).
3. Elevate that user to `ADMIN` (operator action, ADR-0019):
   `UPDATE users SET role = 'ADMIN' WHERE email = '…';`
4. Sign in and confirm the **Administration** item appears in the sidebar.

## Accounts & keys

- **Passwords** are hashed with Argon2id; only hashes are stored.
- **API keys** (if used) are shown once at creation and stored only as a
  SHA-256 hash; revoke from the user's profile/admin surface.
- **Sessions** use short-lived JWT access tokens with single-use, rotating
  refresh tokens (reuse is detected and rejected).

## Pilot mode

When `ATHENA_PILOT_MODE=true`, `GET /pilot/status` reports the decision-support
posture (`order_execution:false`, `broker_integration:false`,
`human_approval_required:true`). The flag surfaces posture to operators and
gates the daily pilot report; it changes no business logic. See `PILOT_MODE.md`.

## Health & monitoring

- `GET /health` — liveness.
- `GET /health/full` — per-component status (database, redis, snapshots) plus
  `pilot_mode`. Restricted to the ops network.
- `GET /metrics` — Prometheus exposition. Grafana dashboards and alerting are
  described in `OBSERVABILITY.md`.

The in-app **notification bell** surfaces review backlog and degraded
components to signed-in users; it is not a substitute for Prometheus alerting.

## Data & reports

- Provider sync (prices, macro), KG sync and the daily pilot report run as
  scheduled jobs — see `DEPLOYMENT.md` §Scheduled jobs and `RUNBOOK.md`.
- User-facing reports are generated client-side (Reports page); no server
  report store is required.

## Backups, DR, incidents

- Backups & restore drills: `scripts/backup.sh`, `scripts/restore.sh`,
  `docs/DR_CHECKLIST.md`.
- Incident playbooks: `INCIDENT_RESPONSE.md`.
- Disaster recovery scenarios: `docs/DR_PLAN.md`.

## Guardrails you must preserve
Athena must never execute trades or connect to a broker. There is no execution
path in the codebase; keep it that way. LLMs may summarize/explain/extract but
must never produce BUY/SELL decisions (ADR-0003).
