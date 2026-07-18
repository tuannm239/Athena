# ATHENA v1.0 — Release

**Status:** Ready for internal release · **Date:** 2026-07-18

## Product Overview

**Athena is a Financial Decision Intelligence Platform.** It improves
investment **decision quality** through explainable, probabilistic, risk-aware
reasoning. Athena turns market data, fundamentals and evidence into
**Decision Objects** — each with a hypothesis, probability, confidence,
evidence for and against, and a risk assessment — for a human to review and
approve.

Athena is **not** a trading bot, screener, chatbot or signal generator. It
**executes no trades, connects to no broker, and requires human approval for
every decision.** These are structural guarantees, verifiable at
`GET /pilot/status` (`order_execution:false`).

## Features

### Decisioning
- **Decision Center** — every evaluated hypothesis, filterable by lifecycle
  status, with saved filters and export.
- **Decision detail** — probability/confidence gauges, expected utility/return/
  drawdown, full risk assessment, supporting/contradicting/neutral evidence,
  explanation, assumptions, invalidation conditions, human review, and an
  immutable audit trail.
- **Human-in-the-loop lifecycle:** `DRAFT → UNDER_REVIEW → APPROVED | REJECTED
  → ARCHIVED`.

### Dashboard (10 widgets)
Market Overview · Decision Summary · Pending Reviews · Portfolio Summary ·
System Health · Latest Evidence · Market Regime · Risk Distribution ·
Probability Distribution · Recent Activities.

### Productivity
- **Command palette & global search** (⌘K / Ctrl K) across pages, reports,
  decisions and companies; fully keyboard-driven, with a `?` shortcut help.
- **In-app notifications** — review reminders, pipeline/provider/system alerts.
- **Export** — CSV, Excel (.xlsx), PDF, JSON, everywhere data is shown.
- **Reports** — Decision, Portfolio, Risk, Backtest, Scenario, Daily, Weekly,
  Monthly.
- **Personalization** — favorites, recent items, pinned companies, saved
  filters, and preferences (theme, density, reduce-motion, landing page).

### Intelligence & analysis
Research, Knowledge Graph, Feature Store, Probability, Market, Backtest, and
Scenario Simulator surfaces (some awaiting their live data feed).

### Platform
Modular monolith (DDD/Clean/Hexagonal), FastAPI + SQLAlchemy 2 backend,
Next.js/React frontend, PostgreSQL/DuckDB/Redis, behind an Nginx TLS edge with
Prometheus/Grafana/Alertmanager. LLMs may explain/summarize/extract but never
produce decisions (ADR-0003).

## Screenshots

Not included in this document (headless build environment). Reproduce locally:

```bash
cd web && pnpm install && pnpm dev      # http://localhost:3000
```

Key views to capture: Dashboard (`/`), Decision detail (`/decisions/{id}`),
Reports (`/reports`), and the command palette (⌘K).

## Deployment Instructions

Full detail in `DEPLOYMENT.md`. In brief:

```bash
cp .env.production.example .env.production        # fill real secrets
docker compose -f docker-compose.prod.yml --env-file .env.production config >/dev/null
# TLS bootstrap (Let's Encrypt) — see DEPLOYMENT.md
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build
docker compose -f docker-compose.prod.yml --env-file .env.production exec api alembic upgrade head
curl -fsS https://$ATHENA_DOMAIN/health
```

Upgrades from an earlier deployment: see `docs/release/UPGRADE_GUIDE.md`
(v1.0 is additive; no breaking API or schema changes).

## User Documentation

Under `docs/product/`:
- [Quick Start](docs/product/QUICK_START.md)
- [User Guide](docs/product/USER_GUIDE.md)
- [Administrator Guide](docs/product/ADMINISTRATOR_GUIDE.md)
- [Troubleshooting](docs/product/TROUBLESHOOTING.md)
- [Architecture Overview](docs/product/ARCHITECTURE_OVERVIEW.md)
- [API Usage Guide](docs/product/API_USAGE.md)

Release docs under `docs/release/`: Release Notes, Known Issues, Upgrade Guide,
Version History, Roadmap.

## Known Limitations

Summary (full list in `docs/release/KNOWN_ISSUES.md`):
- Some views use clearly-labelled **sample** data until live feeds connect;
  one production provider (Alpha Vantage) is wired.
- Backtest/Scenario reports await their REST data source.
- Reports and global search are client-side; notifications are in-app only.
- No OpenTelemetry tracing; per-process rate limiter (bounded at the edge).
- Two low/moderate **dev/build-only** web dependency advisories (not in the
  production runtime), accepted and tracked.

None blocks the human-in-the-loop internal pilot.

## Future Roadmap

Highlights (full list in `docs/release/ROADMAP.md`): live data feeds and more
providers, Backtest/Scenario endpoints, server-side search, shared Redis rate
limiter, OpenTelemetry tracing, report scheduling, richer notifications, and
in-product calibration/drift and portfolio-optimization surfaces. **The safety
posture never changes** — no execution, no broker, human approval always.

## Release Checklist

- [x] All nine Phase-6 workstreams delivered (UX polish, dashboard, reports,
      search, notifications, export, UX personalization, documentation, release).
- [x] No new investment algorithms; no architecture changes; no backend
      redesign; no breaking API changes.
- [x] Web gates green: typecheck, ESLint, unit tests (76 passing), production
      build.
- [x] Backend unchanged and previously validated (Phase 5: 365 tests, 95.57%
      coverage, mypy strict, ruff clean).
- [x] Documentation complete (product + release).
- [x] Safety constraints verified: no execution/broker path; human approval
      mandatory; audit trail intact; LLMs never decide.
- [ ] Screenshots captured from a running instance (local step).
- [ ] Tag `v1.0` and publish the GitHub release from the prepared draft
      (`docs/release/GITHUB_RELEASE_DRAFT.md`).
- [ ] Product-owner sign-off for internal rollout.

---

*Athena improves decision quality; the human decides. Every recommendation is
explainable, every model backtestable, every business rule testable.*
