# Athena v1.0 — Known Issues & Limitations

Honest limitations at v1.0. None blocks the human-in-the-loop internal pilot.

## Data & feeds

- **Sample data for some views.** Market, company fundamentals and a few
  intelligence views fall back to clearly-labelled **sample** data until their
  live feed/endpoint is connected. Toggle via Settings → Show sample data.
- **One production provider.** Only the Alpha Vantage adapter is wired (daily
  equity + FX). VN-native ticker coverage is limited (ADR-0020). Adding a
  provider is a new adapter, no pipeline change.
- **Backtest / Scenario reports** show "awaiting data feed" — those REST data
  sources are not yet exposed. Decision, Risk, Portfolio and periodic reports
  are fully live.

## Product surface

- **Reports are client-side.** Generated in the browser from loaded data; there
  is no server-side scheduled report store for user reports (the operational
  pilot daily report is separate and server-side).
- **Notifications are in-app only** by design — no email/SMS.
- **Search is client-side** over loaded data plus direct ticker lookup; there is
  no full-text server search endpoint yet.
- **No self-service password reset** in the pilot; an admin resets credentials.

## Platform

- **No OpenTelemetry tracing** — correlation is via structured logs and
  `X-Request-ID`, not distributed spans.
- **Per-process API rate limiter** — bounded globally by the Nginx edge zone; a
  shared Redis limiter is deferred (ADR-0019).
- **Web dev/build dependencies** carry two low/moderate advisories
  (postcss build-time, elliptic via Storybook) — not in the production runtime;
  accepted and tracked (`SECURITY_HARDENING_REPORT.md`).

## Environment notes

- Container images are built and run on the target host; the authoring
  environment validated compose/config statically.

Tracked improvements are in `ROADMAP.md`.
