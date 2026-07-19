# Athena — Vietnam Edition (Phase 7)

**Status:** Ready for daily use by a Vietnamese long-term investor (pilot).
**Focus:** the Vietnamese stock market **exclusively** — HOSE, HNX, UPCoM.

Athena VN Edition is a decision-support system optimized for long-term
investing in Vietnam. It helps a Vietnamese investor reason about listed
companies with explainable fundamentals, evidence and probability — and then
**the investor decides**. It does not trade.

## Non-negotiable guardrails

- **No automatic trading.** Athena never places orders.
- **No broker integration.** No brokerage/API connection exists.
- **Human approval is mandatory** for every decision.
- **No derivatives** (futures, covered warrants) and **no margin** — long-only,
  unleveraged holdings only.
- **Long-term investing** is the design bias throughout (fundamentals, quality
  scores, quarterly/annual cadence), not intraday trading.

These are structural: `GET /pilot/status` reports `order_execution:false`, and
the portfolio corporate-actions module contains no leverage or margin maths.

## What the VN Edition adds

### Market data & reference (WS1)
- Exchanges **HOSE / HNX / UPCoM** with their real daily price-limit bands
  (±7% / ±10% / ±15%) and board lots.
- Indices **VNINDEX, VN30, HNX-Index, HNX30, UPCoM-Index**.
- ICB-aligned **sector taxonomy**, **corporate-action types**, VN **session
  clock**, and a **trading calendar** (weekends + configurable public holidays;
  fixed national holidays seeded, lunar holidays supplied per year).
- `backend/market/domain/vietnam.py` (pure, tested).

### Company analysis & quality scores (WS2)
For every company, from its financial statements (Decimal, guarded):
ROE, ROA, gross/operating/net margin, D/E, current ratio, free cash flow,
EPS, BVPS, P/E, P/B, EV/EBITDA, plus quarterly & annual growth — and
**explainable quality / valuation / growth scores** with documented VN
long-term thresholds. `backend/company/domain/fundamentals.py` (pure, tested).

### Vietnam market dashboard (WS3)
VNINDEX/VN30 and HNX indices, market regime, **breadth** (advancers/decliners,
new highs/lows), **liquidity** and **foreign / proprietary** net flows,
**sector heatmap**, and **top gainers / losers / volume** (`/market`).

### Decision workspace per company (WS4)
`/companies/{ticker}` — fundamentals, quality/valuation/growth gauges, an
**investment thesis** with **bull case / bear case / risks / catalysts**
derived transparently from the fundamentals, **probability / confidence /
expected utility** from a linked decision, and **historical decisions**.

### Portfolio (WS5)
Vietnamese equities, cash, and **corporate actions** — cash dividends, bonus
shares, rights issues, stock splits — plus **sector exposure** and
dividend-inclusive **total return**. No derivatives, no margin.
`backend/portfolio/domain/corporate_actions.py` (pure, tested).

### Research (WS6)
`/research` organizes the evidence corpus by **Company / Industry / Sector /
Macro / Regulations**; every research note links back to its decision history.

### Watchlist (WS7)
`/watchlist` — followed (pinned/favorited) companies with upcoming
**quarterly report / annual report / AGM / dividend** reminders on the
Vietnamese filing cadence.

### Reporting (WS8)
`/reports` — **Daily Market Report (VN)**, Weekly Portfolio Review, Monthly
Decision Review, Quarterly Company Review, plus Decision/Portfolio/Risk —
exportable to **PDF, Excel, CSV, JSON**, generated in the browser.

## Daily use — a Vietnamese investor's loop

1. Open the **Vietnam Market** dashboard: indices, breadth, foreign flows,
   sector heatmap, movers.
2. Check the **Watchlist** for upcoming reports/AGM/dividends on followed names.
3. Open a **company workspace** to review fundamentals, quality scores, and the
   bull/bear/risks/catalysts thesis.
4. Record or review a **decision** (probability, confidence, evidence) and
   **approve or reject** it yourself — Athena never acts.
5. Export a **report** (daily market, quarterly company review) as needed.

## Known limitations (honest)

- **Live VN data feeds are not yet connected.** Market snapshot, company
  fundamentals and the corporate calendar currently use **clearly-labelled
  sample data / rules-based projections**; they populate automatically once the
  live feeds (`/market/vn/snapshot`, `/companies/{ticker}/fundamentals`) are
  served. The backend fundamentals and VN reference logic are real and tested.
- Decisions are not yet ticker-keyed in the API; the company workspace matches
  history heuristically by ticker in the hypothesis.
- Lunar-calendar holidays (Tết, Hùng Kings) must be supplied per year.

## Quality

Backend: full suite **397 passed / 2 skipped**, mypy strict clean, ruff clean —
including 32 VN-specific unit tests (fundamentals, market reference/calendar,
corporate actions). Web: typecheck, ESLint, **81 unit tests**, production build
— all green. No breaking API changes; architecture and guardrails unchanged.

---

*Optimized for long-term investing in the Vietnamese market. Athena assists;
the investor decides.*
