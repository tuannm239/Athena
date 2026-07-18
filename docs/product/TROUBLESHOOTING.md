# Athena — Troubleshooting Guide

Common issues and how to resolve them, for users and operators.

## Sign-in & sessions

**"Invalid credentials" on login.**
Check email/password. Passwords are case-sensitive. If forgotten, an admin must
reset it (there is no self-service email reset in the pilot).

**Logged out unexpectedly / requests fail after idle.**
Access tokens are short-lived and refresh automatically; if the refresh token
expired or was rotated on another device, sign in again. Operators: ensure
`JWT_SECRET` is identical across all API replicas — a mismatch invalidates
tokens.

**403 Forbidden on an action.**
Your role lacks permission. Creating/reviewing decisions needs `ANALYST`;
administration needs `ADMIN`. Ask an admin to adjust your role.

## Data looks like "sample"

A **sample** badge means the live feed for that view is not connected yet;
Athena shows clearly-labelled placeholder data so the UI stays usable. This is
expected until the corresponding provider/endpoint is live. Turn it off in
**Settings → Show sample data** if you prefer empty states.

## Notifications

**A notification won't go away.**
Dismiss it with the × — dismissed items stay dismissed. Derived alerts (review
backlog, health) reappear only if the underlying condition recurs.

**Bell shows a count I don't expect.**
The count is unread items; open the panel to mark all read. Review reminders
reflect decisions currently in `UNDER_REVIEW`.

## Export & reports

**Export button is disabled.**
There are no rows to export for the current view/filter. Adjust the filter or
pick a report with data.

**Excel/PDF didn't download.**
The browser may have blocked the download or a pop-up. Allow downloads for the
site and retry. Export runs entirely in the browser; no server call is made.

**A report says "awaiting data feed".**
Backtest/Scenario reports need a REST data source that is not yet exposed. Use
Decision, Risk, Portfolio, or the periodic reports meanwhile.

## Performance / display

**UI feels cramped or too spacious.**
Toggle **Settings → Density** (comfortable/compact).

**Too much motion.**
**Settings → Reduce motion** (also auto-honored if your OS requests reduced
motion).

## Operator diagnostics

**`/health/full` shows a component degraded.**
Degraded ≠ down — it names the failing component (database/redis/snapshots).
Redis is a cache (ephemeral); the API continues. See `INCIDENT_RESPONSE.md`.

**High latency or 5xx.**
Check the Grafana **API** dashboard and `level=ERROR` logs; correlate by
`X-Request-ID`. See `OBSERVABILITY.md`.

**Backend errors carry an `X-Request-ID`.**
Quote it when reporting an issue — it correlates the edge, app and decision
trace in the logs.

## Still stuck?
Capture the screen, the `X-Request-ID` if shown, and the steps to reproduce,
and contact your administrator.
