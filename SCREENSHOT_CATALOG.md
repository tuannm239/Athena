# Athena — Screenshot Catalog

Screenshots of **every page** in the Athena web application, captured from the
production build with Playwright + the pre-installed Chromium. Images live in
`web/tests/e2e/screenshots/` (full-page PNGs).

## How they were generated

```bash
cd web && pnpm exec playwright test screenshots
```

`tests/e2e/screenshots.spec.ts` authenticates via a stubbed refresh token and
stubs the backend at the network layer, so each of the 23 routes renders
hermetically and is captured full-page. Regenerating overwrites the PNGs.

## Catalog (23 pages)

| # | Page | Route | File |
|---|---|---|---|
| 1 | Login / Register | `/login` | `login.png` |
| 2 | Dashboard (home) | `/` | `dashboard.png` |
| 3 | Vietnam Market | `/market` | `market.png` |
| 4 | Companies | `/companies` | `companies.png` |
| 5 | Company Workspace (12 tabs) | `/companies/HPG` | `company-workspace.png` |
| 6 | Research | `/research` | `research.png` |
| 7 | Evidence Center | `/evidence` | `evidence.png` |
| 8 | Decision Center | `/decisions` | `decisions.png` |
| 9 | Portfolio | `/portfolio` | `portfolio.png` |
| 10 | Watchlist | `/watchlist` | `watchlist.png` |
| 11 | Knowledge Graph | `/knowledge-graph` | `knowledge-graph.png` |
| 12 | Probability Studio | `/probability` | `probability.png` |
| 13 | Backtest | `/backtest` | `backtest.png` |
| 14 | Scenario Simulator | `/scenario` | `scenario.png` |
| 15 | Feature Store | `/feature-store` | `feature-store.png` |
| 16 | Reports | `/reports` | `reports.png` |
| 17 | Notifications | `/notifications` | `notifications.png` |
| 18 | Settings | `/settings` | `settings.png` |
| 19 | Profile | `/profile` | `profile.png` |
| 20 | Help Center | `/help` | `help.png` |
| 21 | About | `/about` | `about.png` |
| 22 | Feedback | `/feedback` | `feedback.png` |
| 23 | Release Notes | `/release-notes` | `release-notes.png` |

## Notes

- Captures use hermetic network stubs; where a live Vietnamese feed is not
  connected the pages render clearly-labelled **sample** data (as they do in
  the real app until the feed is live).
- The run doubles as a smoke test: it caught and we fixed a render-loop bug
  (zustand selectors returning fresh arrays) before finalizing — every page now
  renders without console/runtime errors.
