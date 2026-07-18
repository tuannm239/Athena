"""W6 supplementary: walk-forward, rolling-window, block-bootstrap and
regime-stress analysis; and W7 human-review override simulation.
Reads study.json for the 20-seed Monte Carlo, and regenerates a few
panels for regime-conditioned (stress) analysis."""

from __future__ import annotations

import json
import math
import random
import statistics
from pathlib import Path

import research.vn_market as vm
from research.replay_decisions import replay
from research.study import _by_month, _mean, _select_top

STUDY = Path(__file__).resolve().parents[1] / "research" / "experiments" / "study.json"


def sharpe_monthly(rets: list[float]) -> float:
    if len(rets) < 2:
        return 0.0
    mu = _mean(rets)
    sd = statistics.pstdev(rets)
    return (mu / sd * math.sqrt(12)) if sd else 0.0


def main() -> None:
    d = json.loads(STUDY.read_text())
    per = d["per_seed"]

    # ---------- Monte Carlo (20 independent market histories) ----------
    ath_cagr = [p["strategies"]["Athena"]["cagr"] for p in per]
    ath_sh = [p["strategies"]["Athena"]["sharpe"] for p in per]
    print("=== MONTE CARLO (20 seeds) ===")
    print(
        f"Athena CAGR  mean={statistics.mean(ath_cagr):.4f} sd={statistics.pstdev(ath_cagr):.4f} "
        f"min={min(ath_cagr):.4f} max={max(ath_cagr):.4f}"
    )
    print(
        f"Athena Sharpe mean={statistics.mean(ath_sh):.4f} sd={statistics.pstdev(ath_sh):.4f} "
        f"min={min(ath_sh):.4f} max={max(ath_sh):.4f}"
    )
    beat = statistics.mean(
        [
            1.0
            if p["strategies"]["Athena"]["sharpe"] > p["strategies"]["VNINDEX"]["sharpe"]
            else 0.0
            for p in per
        ]
    )
    print(f"P(Athena Sharpe > VNINDEX) across seeds = {beat * 100:.0f}%")

    # ---------- Walk-forward (4 sequential folds, pooled monthly returns) ----------
    print("\n=== WALK-FORWARD (4 sequential folds, monthly returns pooled over seeds) ===")
    folds = 4
    for f in range(folds):
        a_all, v_all = [], []
        for p in per:
            am = p["strategy_monthly"]["Athena"]
            vmn = p["strategy_monthly"]["VNINDEX"]
            k = len(am) // folds
            a_all += am[f * k : (f + 1) * k]
            v_all += vmn[f * k : (f + 1) * k]
        print(
            f"  fold {f + 1}: Athena Sharpe={sharpe_monthly(a_all):.3f}  "
            f"VNINDEX Sharpe={sharpe_monthly(v_all):.3f}  "
            f"AthenaMeanRet={_mean(a_all):+.4f} vs {_mean(v_all):+.4f}"
        )

    # ---------- Rolling 24-month window (seed 0) ----------
    print("\n=== ROLLING 24-MONTH WINDOW (seed 0) ===")
    am = per[0]["strategy_monthly"]["Athena"]
    vmn = per[0]["strategy_monthly"]["VNINDEX"]
    W = 24
    wins = 0
    tot = 0
    a_sh_list = []
    for i in range(0, len(am) - W):
        a = sharpe_monthly(am[i : i + W])
        v = sharpe_monthly(vmn[i : i + W])
        a_sh_list.append(a)
        wins += 1 if a > v else 0
        tot += 1
    print(
        f"  windows={tot}  Athena>VNINDEX in {wins}/{tot} ({wins / tot * 100:.0f}%)  "
        f"mean rolling Athena Sharpe={statistics.mean(a_sh_list):.3f}"
    )

    # ---------- Block bootstrap CI on Athena Sharpe (seed 0, 6-month blocks) ----------
    print("\n=== BLOCK BOOTSTRAP (seed 0, 6-month blocks, 5000 resamples) ===")
    rng = random.Random(11)
    B = 6
    blocks = [am[i : i + B] for i in range(0, len(am) - B, B)]
    boot = []
    for _ in range(5000):
        sample = []
        while len(sample) < len(am):
            sample += blocks[rng.randrange(len(blocks))]
        boot.append(sharpe_monthly(sample[: len(am)]))
    boot.sort()
    print(
        f"  Athena Sharpe point={sharpe_monthly(am):.3f}  "
        f"95% CI=[{boot[125]:.3f}, {boot[4875]:.3f}]"
    )

    # ---------- Regime stress (regenerate panels, condition on CONTRACTION) ----------
    print("\n=== STRESS: performance in CONTRACTION-regime months (5 seeds) ===")
    a_stress, v_stress, a_calm, v_calm = [], [], [], []
    for seed in d["seeds"][:5]:
        panel = vm.generate_market(seed=seed)
        records = replay(panel)
        bm = _by_month(records)
        for mo in sorted(bm):
            recs = bm[mo]
            day = recs[0].day
            regime = panel.regimes[day]
            mkt = recs[0].mkt_fwd_return
            ath = _mean([r.fwd_return for r in _select_top(recs, lambda r: r.posterior, 0.2)])
            if regime == "CONTRACTION":
                a_stress.append(ath)
                v_stress.append(mkt)
            else:
                a_calm.append(ath)
                v_calm.append(mkt)
    print(
        f"  CONTRACTION months: n={len(a_stress)}  Athena mean={_mean(a_stress):+.4f}  "
        f"VNINDEX mean={_mean(v_stress):+.4f}  edge={_mean(a_stress) - _mean(v_stress):+.4f}"
    )
    print(
        f"  EXPANSION months:   n={len(a_calm)}  Athena mean={_mean(a_calm):+.4f}  "
        f"VNINDEX mean={_mean(v_calm):+.4f}  edge={_mean(a_calm) - _mean(v_calm):+.4f}"
    )


if __name__ == "__main__":
    main()
