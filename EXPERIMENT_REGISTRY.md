# ATHENA — Experiment Registry (Phase 4)

Every Phase 4 result is reproducible from commit
`b242881a3a0e8769f612c3ec4eb17854ab067894` using the deterministic
harnesses under `research/`. All randomness is seeded; no network or
external data is used.

## Environment

| Field | Value |
|---|---|
| Python | 3.13 (`/usr/bin/python3.13`, project `.venv`) |
| Key libs | polars 1.42.1; pure-Python stats (no numpy/scipy available) |
| Athena code | commit `b242881` (engines frozen; Phase 4 adds `research/` only) |
| Determinism | all experiments seeded; identical inputs → identical outputs |

## Harnesses

| File | Purpose | Lines |
|---|---|---|
| `research/vn_market.py` | Seeded synthetic VN market DGP + stat helpers | — |
| `research/replay_decisions.py` | Replays Athena RFC-0026 decisions over the market | — |
| `research/study.py` | Full metric study (W2–W8) per seed + multi-seed driver | — |
| `research/aggregate.py` | Cross-seed aggregation + paired bootstrap significance | — |
| `research/portfolio_extra.py` | W6 walk-forward / rolling / bootstrap / stress | — |
| `research/human_review.py` | W7 override simulation | — |

## Registered experiments

| ID | Workstream | Command | Seeds | Exec time | Output |
|---|---|---|---|---|---|
| E01 | W1 Historical Replay | `python -m research.vn_market` | 20260718 | 2.4 s | stdout stylized facts |
| E02 | W2 Decision Validation | `python -m research.study --seeds 20` | 20260718–37 | 96.9 s | `experiments/study.json` |
| E03 | W3 Calibration | `python -m research.aggregate` | (reads E02) | <1 s | stdout pooled bins, ECE |
| E04 | W4 Feature Importance | `python -m research.aggregate` | (reads E02) | <1 s | stdout corr/MI/perm/Shapley |
| E05 | W5 Drift | `python -m research.aggregate` | (reads E02) | <1 s | stdout PSI, early/late |
| E06 | W6 Portfolio | `python -m research.portfolio_extra` | 20260718–37 (+5 for stress) | 33 s | stdout MC/WF/roll/boot/stress |
| E07 | W7 Human Review | `python -m research.human_review` | 20260718–22 | 20 s | stdout override analysis |
| E08 | W8 Benchmark | `python -m research.aggregate` | (reads E02) | <1 s | stdout league + significance |

## Full reproduction (one shot)

```bash
cd /home/user/Athena
python -m research.study --seeds 20        # E02 -> experiments/study.json  (~97s)
python -m research.aggregate               # E03,E04,E05,E08
python -m research.portfolio_extra         # E06  (~33s)
python -m research.human_review            # E07  (~20s)
python -m research.vn_market               # E01
```

## Configuration constants (frozen for this program)

| Constant | Value | Location |
|---|---|---|
| base seed | 20260718 | `study.BASE_SEED` |
| years / days | 16 / 4 032 | `vn_market.generate_market` |
| companies / sectors | 120 / 8 | `vn_market` |
| forward horizon / rebalance | 21 / 21 trading days | `replay_decisions` |
| selection fraction (Athena/factor) | top 20 % | `study.strategy_returns` |
| true premia (Q/M/V, annualised) | 0.14 / 0.12 / 0.10 | `vn_market` |
| bootstrap resamples | 5 000 | `study.bootstrap_diff_ci` |

## Provenance & integrity

- No experiment reads external data; all inputs are seed-derived.
- `experiments/study.json` (1.2 MB) is the canonical result artifact for
  E02–E05, E08; regenerating with the same seeds reproduces it exactly.
- A **testbed defect was found and fixed** during Phase 4 (VN30 selected
  by end-of-sample cap = look-ahead bias → corrected to start-of-sample,
  point-in-time). This affected the research harness only, not Athena
  engine code. No Athena implementation change was made.
