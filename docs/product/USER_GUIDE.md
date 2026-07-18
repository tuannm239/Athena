# Athena — User Guide

A tour of every screen and feature. Athena is decision **support**: it
generates Decision Objects with evidence, probability and risk; a human
approves or rejects them. It executes no trades and integrates no broker.

## Global features

### Command palette (⌘K / Ctrl K)
Search across pages, reports, recent items, favorites, decisions and companies
(type a ticker for a direct lookup). Navigate with ↑/↓, open with Enter, close
with Esc.

### Notifications (bell)
In-app only. Sources:
- **Review reminders** — decisions in `UNDER_REVIEW`.
- **Pipeline** — data snapshot store degraded.
- **Provider** — a market feed running on clearly-labelled sample data.
- **System** — database/redis health.
Resolved conditions clear automatically; dismiss anything manually.

### Export
Anywhere you see **Export**, download **CSV / Excel (.xlsx) / PDF / JSON**.
Generation is entirely in your browser; nothing is uploaded.

### Keyboard shortcuts (press ?)
⌘/Ctrl K palette · ? help · ↑↓ move · Enter open · Esc close.

## Screens

### Dashboard (`/`)
Ten at-a-glance widgets: Market Overview, Decision Summary, Pending Reviews,
Portfolio Summary, System Health, Latest Evidence, Market Regime, Risk
Distribution, Probability Distribution, and Recent Activities. Widgets that
depend on a not-yet-live feed show a **sample** badge.

### Decision Center (`/decisions`)
The list of every hypothesis Athena has evaluated. Filter by lifecycle status
(`DRAFT`, `UNDER_REVIEW`, `APPROVED`, `REJECTED`, `ARCHIVED`), **save filters**
for reuse, and **export** the current view.

### Decision detail (`/decisions/{id}`)
Everything about one decision:
- **Probability & confidence** gauges.
- **Expected utility / return / drawdown**.
- **Risk assessment** — VaR, CVaR, max drawdown, stress, liquidity, and a
  risk level (`VERY_LOW`…`CRITICAL`).
- **Evidence** — each item is Supporting / Contradicting / Neutral, with a
  source, category, reliability and explanation. LLM-extracted evidence is
  labelled as such. Export all evidence from here.
- **Explanation, assumptions, invalidation conditions**.
- **Human review** — approve or reject with a note. This is mandatory.
- **Audit trail** — the immutable record of changes.
Star a decision to add it to **Favorites**; visiting it adds it to **Recent**.

**Decision lifecycle:** `DRAFT → UNDER_REVIEW → APPROVED | REJECTED → ARCHIVED`.
Only a human moves a decision to APPROVED or REJECTED.

### Companies (`/companies`)
Look up a company by ticker to see its profile (exchange, sector, industry,
currency). Pin companies for quick access. Where live fundamentals are not yet
connected, sample data is clearly labelled.

### Portfolio (`/portfolio`)
Holdings, allocation, cash and unrealized P&L per position. Export positions.

### Market (`/market`)
Market regime and context scores (liquidity, breadth, volatility, rotation).

### Research, Knowledge Graph, Feature Store, Probability
Intelligence tooling that explains the reasoning behind decisions —
relationships between entities, the feature catalogue, and probability
calibration. Some views await their live data feed and say so.

### Backtest (`/backtest`) & Scenario Simulator (`/scenario`)
Analysis tools for historical performance and what-if scenarios.

### Reports (`/reports`)
Generate **Decision, Portfolio, Risk, Backtest, Scenario, Daily, Weekly,
Monthly** reports as PDF or Excel. Decision/Risk/Portfolio and the periodic
reports build from live data; Backtest/Scenario show "awaiting data feed" until
their REST source is exposed. Deep-link a specific report with `?kind=...`.

### Settings (`/settings`)
Theme, density, reduce-motion, landing page; manage favorites, pinned
companies and recent items.

### Profile (`/profile`)
Your account and API keys (if enabled).

### Administration (`/admin`) — admins only
User and system administration (see the Administrator Guide).

## The golden rule
Athena improves **decision quality**; it never allocates capital. Every
recommendation is explainable and every decision requires your approval.
