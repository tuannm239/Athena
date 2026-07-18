# Athena v1.0 — Release Notes

**Release:** v1.0 (internal) · **Date:** 2026-07-18
**Theme:** Productization — Athena is now a polished, usable product on top of
the completed platform.

Athena is a **Financial Decision Intelligence Platform**. It generates
explainable, probabilistic, risk-aware **Decision Objects** for a human to
approve. It executes no trades and connects to no broker.

## Highlights (Phase 6)

- **Command palette & global search (⌘K / Ctrl K)** — jump to any page or find
  decisions, companies and reports instantly; fully keyboard-driven.
- **Redesigned dashboard** — ten at-a-glance widgets: Market Overview, Decision
  Summary, Pending Reviews, Portfolio Summary, System Health, Latest Evidence,
  Market Regime, Risk Distribution, Probability Distribution, Recent Activities.
- **In-app notifications** — review reminders and pipeline/provider/system
  alerts, derived from live signals. No email/SMS.
- **Export everywhere** — CSV, Excel (.xlsx), PDF and JSON from decisions,
  portfolio and evidence, generated entirely in the browser.
- **Reports** — Decision, Portfolio, Risk, Backtest, Scenario, Daily, Weekly
  and Monthly reports as PDF/Excel.
- **Personalization** — favorites, recent items, pinned companies, saved
  filters, and preferences (theme, density, reduce-motion, landing page).
- **UX polish & accessibility** — keyboard-shortcut help (`?`), skip-link,
  visible focus rings, density and reduced-motion support, mobile navigation.
- **Product documentation** — Quick Start, User, Administrator, Troubleshooting,
  Architecture and API guides (`docs/product/`).

## Included from earlier phases

- Full decision platform: Decision Kernel, Probability, Risk, Portfolio,
  Market Regime, Behavior (advisory), Knowledge Graph, Feature Store, Data
  Pipeline, Backtest, Scenario Simulator.
- Production deployment: multi-stage images, Nginx TLS edge, CI/CD with CVE +
  image scanning, Prometheus/Grafana/Alertmanager observability.
- Pilot mode (read-only, human-in-the-loop) with audit-backed daily reports.
- First production data-provider adapter (Alpha Vantage).

## Compatibility

- **No breaking API changes.** All Phase 6 work is additive and frontend-side;
  the SPEC-08 REST contract is unchanged.
- **No new investment algorithms; no architecture changes; no backend
  redesign.** The Decision Kernel remains the sole owner of business logic.

## Constraints preserved (non-negotiable)

No trade execution · no broker integration · Decision Objects only · human
approval mandatory · full audit trail · LLMs never produce decisions.

See `KNOWN_ISSUES.md` for limitations and `ROADMAP.md` for what's next.
