# Athena Web Application — v1.0

A complete, production-quality web application for **Financial Decision
Intelligence** on the Vietnamese market. A first-time user can run their entire
daily investment workflow inside Athena without opening any other application.

> Athena is decision **support**: it produces Decision Objects with explainable
> fundamentals, evidence and probability; the human approves. No automatic
> trading, no broker, no derivatives, no margin.

## Complete user journey (no dead ends)

```
Login/Register → Dashboard → Market → Search Company → Company Workspace
  → Research → Decision → Watchlist → Portfolio → Reports → Settings → Logout
```

Every screen connects naturally via the sidebar, the ⌘K command palette, and
in-context links (market movers → company, evidence → decision, etc.).

## Pages (all implemented, no placeholders)

| Area | Route | Notes |
|---|---|---|
| Dashboard | `/` | VN indices, portfolio, today's decisions, decision quality, research, evidence, watchlist, system status, activity, notifications |
| Market | `/market` | VNINDEX/VN30/HNX, breadth, flows, sector heatmap, movers |
| Companies | `/companies` | search + popular/pinned quick-picks |
| Company Workspace | `/companies/{ticker}` | 12 tabs — Overview, Financials, Ratios, Growth, Valuation, Research, Evidence, Decision, Risk, History, Notes, Peers |
| Research | `/research` | upload docs, notes, review, audit + evidence corpus |
| Evidence Center | `/evidence` | all evidence, filter, export |
| Decision Center | `/decisions`, `/decisions/{id}` | thesis, bull/bear, catalysts, risks, evidence, probability, confidence, EU, timeline, review, approval, journal |
| Portfolio | `/portfolio` | holdings, allocation, P&L, sector, cash |
| Watchlist | `/watchlist` | followed companies + report/AGM/dividend reminders |
| Knowledge Graph | `/knowledge-graph` | real decision→evidence graph |
| Probability / Backtest / Scenario / Feature Store | `/probability` `/backtest` `/scenario` `/feature-store` | live, interactive tools |
| Reports | `/reports` | Company/Decision/Portfolio/Research/Market + Daily/Weekly/Monthly → PDF/Excel/CSV/JSON |
| Profile / Admin / Settings | `/profile` `/admin` `/settings` | account, RBAC admin, theme/language/accessibility/security |
| Notifications | `/notifications` | full list, mark-read/dismiss |
| Help / About / Feedback / Release Notes | `/help` `/about` `/feedback` `/release-notes` | support surfaces |

## SaaS-grade UX

Command palette + global search (⌘K) · in-app notifications (bell) · **toasts**
· **confirmation dialogs** · **tabs** · keyboard help (`?`) · register/sign-in ·
theme (dark/light) · density · **high-contrast** · language preference ·
reduce-motion · loading/empty/error states · export everywhere · responsive,
touch-friendly, keyboard-navigable, accessible (skip-link, focus rings, ARIA).

## Performance

Next.js App Router with automatic **code-splitting**; heavy report libraries
(jspdf, write-excel-file) are **dynamically imported** and kept out of the
initial bundle; pure-SVG/CSS charts (no chart library) keep pages light;
static prerendering where possible. First-load JS ~103 KB shared.

## Quality gates

- TypeScript: **0 errors** (`tsc --noEmit`)
- ESLint: **0 warnings** (`next lint`)
- Unit/integration: **90 tests passing** (Vitest)
- E2E: Playwright (auth + workflow), hermetic network stubs
- Production build: **green**, 26 routes

## Data honesty

All UI, navigation, computations (probability, backtest, scenario,
fundamentals, quality scores, corporate actions) and personalization are real.
Where a live Vietnamese feed is not yet connected (market snapshot, company
fundamentals, price paths, corporate calendar), Athena shows **clearly-labelled
sample data** and populates automatically once the endpoints are live. Notes,
attachments, watchlist, feedback and preferences persist in the browser; the
backend is the system of record for decisions and evidence.

## Deployment

Multi-stage Next.js standalone image (`web/Dockerfile`), wired into
`docker-compose.prod.yml` behind the Nginx TLS edge. See `DEPLOYMENT.md`.

## Deliverables

`ATHENA_WEBAPP_V1.md` (this) · `USER_GUIDE.md` · `ADMIN_GUIDE.md` ·
`RELEASE_NOTES.md` · `SCREENSHOT_CATALOG.md` · `USER_ACCEPTANCE_REPORT.md`.
