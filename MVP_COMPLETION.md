# Athena — MVP Completion (Phase 8)

**Goal:** a user can open Athena every day and complete the entire investment
workflow without leaving the application. **No placeholder pages, no unfinished
navigation, no demo screens.**

Athena is decision **support** for the Vietnamese market: it produces Decision
Objects with explainable fundamentals, evidence and probability; the human
approves. It executes no trades, connects to no broker, and models no
derivatives or margin.

## Placeholders eliminated

Every remaining `PendingFeature` demo has been replaced with a functional page
(verified: **zero** `PendingFeature` usages in `app/`):

| Page | Now |
|---|---|
| Probability | Interactive Bayesian calculator (prior + evidence → live posterior) |
| Backtest | Buy-and-hold equity curve + SPEC-09 metrics, computed live |
| Scenario | Real what-if on the actual portfolio (shock equity, preserve cash) |
| Knowledge Graph | Built from **real** decision→evidence data (nodes/edges/links) |
| Feature Store | Searchable catalogue of the features Athena computes |

## The daily workflow (end-to-end, in-app)

| Step | Screen | Status |
|---|---|---|
| Login | `/login` | ✅ |
| Dashboard | `/` — VN indices, portfolio, pending reviews, watchlist, decisions, heatmap, regime, distributions, recent evidence, system status | ✅ |
| Market Overview | `/market` — indices, breadth, foreign/prop flows, sector heatmap, movers (click a ticker → workspace) | ✅ |
| Select Company | `/companies` search + popular/pinned quick-picks → `/companies/{ticker}` | ✅ |
| Company Analysis | Overview, Financials, Charts, Ratios, Research, Evidence, Decision History, Probability, Risk, Valuation, Peer Comparison, Notes — one page | ✅ |
| Research | `/research` — upload PDF/Excel/reports, notes, human review, audit trail + evidence corpus by axis | ✅ |
| Decision | `/decisions`, `/decisions/{id}` — thesis, bull/bear, catalysts, risks, evidence, probability, confidence, expected utility, history, timeline, human approval, Decision Journal | ✅ |
| Watchlist | `/watchlist` — followed companies + quarterly/annual/AGM/dividend reminders | ✅ |
| Portfolio | `/portfolio` — holdings, allocation, P&L, sector, cash | ✅ |
| Decision Review | review panel on the decision page (approve/reject with note) | ✅ |
| Logout | navbar | ✅ |

Global: **⌘K command palette** + search, **notifications bell**, **export**
(CSV/Excel/PDF/JSON), keyboard help (`?`), theme/density/preferences.

## Acceptance criteria — a first-time user can:

1. **Log in** → `/login`. ✅
2. **Review the Vietnamese market** → `/market`. ✅
3. **Search for a company** → `/companies` → opens `/companies/{ticker}`. ✅
4. **Read financial data** → workspace Fundamentals (ROE, margins, P/E, …). ✅
5. **Read research** → `/research` (notes + evidence corpus). ✅
6. **Review Athena's recommendation** → workspace thesis + linked decision
   (probability/confidence/expected utility). ✅
7. **Add the company to a watchlist** → pin from the workspace/market. ✅
8. **Review their portfolio** → `/portfolio`. ✅
9. **Export a report** → `/reports` (one-click PDF/Excel/CSV/JSON). ✅

All without leaving the application.

## What's real vs. clearly-labelled sample

The full UI, navigation, computations (probability, backtest, scenario,
fundamentals ratios, quality scores, corporate actions) and personalization
(watchlist, notes, favorites, saved filters) are **real**. Where a live
Vietnamese market feed is not yet connected, the app shows **clearly-labelled
sample data** (market snapshot, company fundamentals, price paths, corporate
calendar) via the established mock-fallback pattern — these populate
automatically once the backend endpoints (`/market/vn/snapshot`,
`/companies/{ticker}/fundamentals`) serve live data. Notes/attachments are
persisted client-side (localStorage); the backend remains the system of record
for decisions and evidence.

## Guardrails preserved

No automatic trading · no broker integration · human approval mandatory · no
derivatives · no margin · long-term Vietnamese investing. No breaking API
changes; architecture and Decision-Kernel ownership of business logic unchanged.

## Quality

Web: typecheck, ESLint, **86 unit tests**, production build — all green
(20 routes). Backend (unchanged this phase): 397 passed / 2 skipped, mypy
strict, ruff clean.

---

*Athena assists; the investor decides. Open it every day and run the whole
loop — market to decision to review — without leaving.*
