# ATHENA — Research Book (Phase 4, Workstream 1: Historical Replay)

| Field | Value |
|---|---|
| Dataset | Synthetic Vietnamese-market DGP (`research/vn_market.py`) — **not** real VNINDEX/VN30 data |
| Configuration | 16 years, 4 032 trading days, 120 companies, 8 sectors, VN30 = 30 largest by point-in-time cap |
| Random Seed | base 20260718 (+0…+19 for the 20-seed Monte-Carlo panel) |
| Execution Time | market generation ≈ 2.4 s/seed; 20-seed study 96.9 s |
| Version | Athena engines @ commit `b242881`; RFC-0026 probability engine; `athena-dslc/1.0.0` |
| Commit Hash | `b242881a3a0e8769f612c3ec4eb17854ab067894` |
| Reproduce | `python -m research.vn_market` ; `python -m research.study --seeds 20` |

## ⚠️ Data provenance — read first

**No licensed Vietnamese market-data feed is connected to this
environment** (known gap R1, `PRODUCTION_READINESS_REPORT.md`). Real
VNINDEX/VN30/sector/company history is therefore unavailable. Fabricating
15+ years of "real" prices would be scientifically dishonest.

This research instead uses a **fully-specified, seeded synthetic
data-generating process (DGP)** whose ground-truth factor→return
relationship is *known by construction*. This is stronger than a single
historical path for measuring decision quality, because (a) ground truth
is observable, so calibration/accuracy can be measured exactly, and (b)
running many independent seeds yields statistical power a lone history
cannot. **Every conclusion in this program is conditional on the DGP and
must be re-certified against a real feed before live capital use.** The
same harnesses run unchanged once the feed lands.

## DGP specification (calibrated to documented VN stylized facts)

- **Market factor**: regime-switching drift (expansion +22 %/yr,
  contraction −15 %/yr annualised), 22 % annualised vol, occasional
  fat-tail jumps; asymmetric regime persistence (stationary ≈ 76 %
  expansion) → positive long-run equity premium.
- **8 sectors** with sector betas 0.7–1.3 to the market + idiosyncratic
  sector factor (14 % vol).
- **120 companies**, each in a sector, with market beta 0.85–1.15 and
  three persistent, slowly-drifting **hidden factors** — quality, value,
  momentum. True cross-sectional premia (annualised, per unit factor
  deviation): **quality +14 %, momentum +12 %, value +10 %**. Idiosyncratic
  vol 22 %.
- **Observable features** = hidden factors + measurement noise (this is
  what Athena sees). Signal-to-noise at the 1-month horizon is low by
  design — realistic factor investing, where edge emerges through
  diversification, not single-name prediction.
- **VN30** = 30 largest by **start-of-sample** cap (point-in-time, no
  look-ahead).

## Replayed stylized facts (VNINDEX, mean of 5 seeds)

| Statistic | Synthetic value | Documented VN reference |
|---|---|---|
| Annualised return | 11.7 % | ~10–13 % long-run |
| Annualised volatility | 23.9 % | ~20–25 % |
| Max drawdown | −47.0 % | −45 % to −68 % (2008/2018/2022) |
| Sharpe (rf=0) | 0.58 | ~0.4–0.6 |
| Time in expansion | 75.6 % | majority bull, punctuated |
| Sector ann.return spread | 4.2 % (ConsumerStaples) … 13.1 % (Materials) | wide sector dispersion |

The synthetic market reproduces the salient VN characteristics: high
volatility, deep episodic drawdowns, positive long-run drift, strong
sector dispersion and regime structure.

## What is replayed

| Series | Definition |
|---|---|
| VNINDEX | drift+vol regime-switching index level (4 032 daily points) |
| VN30 | equal-weight of 30 largest names (point-in-time) |
| Sector indices | 8 cap-weighted sector level series |
| Individual companies | 120 daily price paths with observable factor features |

## Downstream use

This replayed world is the substrate for Workstreams 2–8: Athena's real
RFC-0026 engine forms a decision per company per month (22 920 decisions
over 191 months per seed), which are then validated against the known
forward outcomes. Experiment provenance and reproduction commands are
registered in `EXPERIMENT_REGISTRY.md`.
