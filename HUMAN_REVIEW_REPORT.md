# ATHENA — Human Review Report (Phase 4, Workstream 7)

| Field | Value |
|---|---|
| Dataset | Synthetic VN market, 5 seeds × 22 920 decisions = 114 600 reviewed decisions |
| Configuration | simulated analyst skill = 0.51; override policy: low-confidence / risk-aversion / contrarian-value |
| Random Seed | 20260718 … 20260722 |
| Execution Time | ≈ 20 s |
| Version | RFC-0026 engine @ `b242881` |
| Commit Hash | `b242881a3a0e8769f612c3ec4eb17854ab067894` |
| Reproduce | `python -m research.human_review` |

## ⚠️ This workstream is a SIMULATION

No real human-reviewer logs exist in this environment. This models a
**modestly-skilled analyst** (independent-call accuracy 0.51) reviewing
each Athena decision, to (a) build and exercise the override-tracking
framework and (b) quantify the *direction* of the human-in-the-loop
effect under stated assumptions. The numbers are illustrative of the
mechanism, not of any specific real analyst. Re-run against real review
logs when the workflow is live.

## Override behaviour

| Metric | Value |
|---|---|
| Override rate | **35.6 %** of decisions |

Override reasons (share of overrides):

| Reason | Share | Trigger |
|---|---|---|
| Low confidence | 70.2 % | Athena confidence below the 25th percentile → analyst substitutes own judgment |
| Risk aversion (contraction) | 24.1 % | analyst vetoes longs during CONTRACTION regimes |
| Contrarian value | 5.7 % | analyst distrusts low-value / high-momentum picks |

## Outcome comparison (mean over 5 seeds)

| Policy | Accuracy | Mean edge / decision |
|---|---|---|
| Athena alone | 0.5147 | **+0.00438** |
| Human alone | 0.5097 | +0.00337 |
| Athena + human override | 0.5195 | +0.00429 |

## Analysis — the central finding

- **The simulated analyst alone is worse than Athena** (accuracy 0.510 vs
  0.515; edge +0.34 % vs +0.44 %). A modestly-skilled human does not beat
  the calibrated system on raw selection — consistent with the
  "algorithm aversion" literature.
- **Blanket override is roughly break-even, tilted by *reason*.** The
  combined policy nudges **accuracy up +0.48 pp** (the contraction
  risk-veto avoids some losers) but nudges **captured edge down −0.009 %**
  (vetoing longs also forgoes some winners). Net economic effect ≈ 0.
- **The value of human review is therefore selective, not universal.**
  The risk-aversion veto in contractions is *defensible* (it aligns with
  the pro-cyclical-edge finding in PORTFOLIO_RESEARCH — factor alpha is
  weak in downturns). The low-confidence overrides (70 % of all overrides)
  neither help nor hurt on average — they mostly add noise.

## Learning opportunities

1. **Route review by confidence, not blanket.** Overriding *low-confidence*
   Athena calls with a barely-skilled human wastes effort (net-zero). The
   productive review target is the **disagreement set** — cases where a
   *skilled* analyst has private information Athena lacks (news, governance,
   liquidity) — which this simulation cannot represent.
2. **Formalise the contraction risk-veto.** The one override that helps is
   regime-conditioned risk aversion. Rather than leaving it to ad-hoc human
   judgment, encode it as a **Risk-engine / Scenario overlay** (already in
   the platform) so it applies consistently — turning an anecdotal human
   habit into a testable rule.
3. **Track override outcomes in production.** Every override is an
   experiment: log (Athena call, human call, outcome) to estimate the
   analyst's *true* skill and the marginal value of each override reason —
   the Behavior engine (SPEC-12) is the natural home for this feedback,
   which is **advisory only** and never overrides the kernel.

## Verdict

Under the modelled assumptions, **human overrides are net-neutral on
average**, with value concentrated in regime-conditioned risk aversion and
waste concentrated in low-confidence blanket overrides. The framework to
measure this is in place; the actionable recommendation is to **review by
disagreement/confidence and codify the useful override (contraction risk)
as a rule**, not to override broadly. Re-run with real reviewer logs to
replace the simulated skill parameter.
