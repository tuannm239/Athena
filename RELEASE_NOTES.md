# Athena — Release Notes

## Web v1.0 — 2026-07-19

The Athena web application is a complete, production-quality product: a
first-time user can run their entire daily investment workflow inside Athena
without opening any other application.

### New in v1.0

- **Complete user journey, no dead ends** — Login/Register → Dashboard →
  Market → Company → Research → Decision → Watchlist → Portfolio → Reports →
  Settings → Logout, connected by sidebar, command palette and in-context links.
- **Every page implemented and polished** — including new **Evidence Center**,
  **Notifications**, **Help Center**, **About**, **Feedback** and **Release
  Notes** pages. Zero placeholder screens.
- **Company Workspace** — one page, twelve tabs (Overview, Financial
  Statements, Ratios, Growth, Valuation, Research, Evidence, Decision, Risk,
  History, Notes, Peers).
- **Research workspace** — upload documents, notes, human review, audit trail.
- **SaaS-grade UX** — toasts, confirmation dialogs, tabs, command palette,
  global search, register flow, keyboard help, theme + density + high-contrast +
  language + reduce-motion, loading/empty/error states.
- **Reports** — one-click Company/Decision/Portfolio/Research/Market and
  Daily/Weekly/Monthly, export to PDF/Excel/CSV/JSON.
- **Interactive tools** — Probability Studio, Backtest, Scenario Simulator,
  Knowledge Graph, Feature Store (all live, real computation/data).
- **Screenshots of every page** generated via Playwright (`SCREENSHOT_CATALOG.md`).

### Fixes

- Fixed a render-loop (React #185) caused by zustand selectors returning fresh
  arrays; every page now renders without console/runtime errors.
- `501 NotImplemented` responses are no longer retried, so clearly-labelled
  sample-data fallbacks appear immediately.

### Quality

TypeScript 0 errors · ESLint 0 warnings · 90 unit tests · Playwright E2E ·
production build green (26 routes). No breaking API changes.

### Known issues

- Some views use clearly-labelled sample data until the live Vietnamese feeds
  are connected.
- Backtest/Scenario reports await their REST data source.
- Notes, attachments, watchlist and feedback persist in the browser in this
  pilot.
- Vietnamese UI localization is a saved preference; copy is being translated.

### Safety posture (unchanged)

No automatic trading · no broker integration · human approval mandatory · no
derivatives · no margin · full audit trail · LLMs never produce decisions.

---

Prior platform/pilot/edition history: `docs/release/VERSION_HISTORY.md`,
`PILOT_RELEASE_v1.0.md`, `ATHENA_VN_EDITION.md`, `MVP_COMPLETION.md`.
