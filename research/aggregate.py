"""Aggregate the multi-seed study into the numbers cited by every Phase 4
report: cross-seed means, paired bootstrap significance of Athena vs each
benchmark, pooled calibration, feature ranking, drift."""

from __future__ import annotations

import json
import statistics
from collections import defaultdict
from pathlib import Path

from research.study import bootstrap_diff_ci

STUDY = Path(__file__).resolve().parents[1] / "research" / "experiments" / "study.json"


def main() -> None:
    d = json.loads(STUDY.read_text())
    per = d["per_seed"]
    ns = len(per)
    print(f"seeds={ns}  commit-basis study generated {d['generated_at']}  elapsed={d['elapsed_s']}s\n")

    # --- decision-quality metrics (W2/W3) ---
    def col(k):
        return [p[k] for p in per]

    for k in ("accuracy", "auc", "brier", "ece", "eu_spread", "stability_flip", "stability_drift", "base_rate_outperform"):
        xs = col(k)
        print(f"{k:24} mean={statistics.mean(xs):.4f}  sd={statistics.pstdev(xs):.4f}  "
              f"min={min(xs):.4f} max={max(xs):.4f}")

    # --- pooled calibration bins ---
    print("\n=== POOLED CALIBRATION (sum over seeds) ===")
    agg = defaultdict(lambda: [0, 0.0, 0.0])  # bin -> [n, sum_p, sum_hit]
    for p in per:
        for lo, n, mp, hr in p["calibration_rows"]:
            if n:
                agg[lo][0] += n
                agg[lo][1] += mp * n
                agg[lo][2] += hr * n
    print(f"{'bin':>6}{'n':>9}{'mean_p':>10}{'hit_rate':>10}{'gap':>9}")
    for lo in sorted(agg):
        n, sp, sh = agg[lo]
        print(f"{lo:>6.1f}{n:>9}{sp/n:>10.4f}{sh/n:>10.4f}{sp/n - sh/n:>+9.4f}")

    # --- feature importance (W4) averaged ---
    print("\n=== FEATURE IMPORTANCE (mean over seeds) ===")
    for method in ("correlation", "mutual_information", "permutation_importance", "shapley"):
        agg2 = defaultdict(list)
        for p in per:
            for f, v in p[method].items():
                agg2[f].append(v)
        ranked = sorted(agg2.items(), key=lambda kv: -statistics.mean(kv[1]))
        print(f"{method:22}", "  ".join(f"{f}={statistics.mean(v):+.4f}" for f, v in ranked))

    # --- drift (W5) ---
    print("\n=== DRIFT (mean over seeds) ===")
    dk = per[0]["drift"].keys()
    for k in dk:
        xs = [p["drift"][k] for p in per]
        print(f"{k:24} mean={statistics.mean(xs):+.4f}  sd={statistics.pstdev(xs):.4f}")

    # --- strategy performance (W6/W8) averaged + significance vs Athena ---
    print("\n=== STRATEGY PERFORMANCE (mean over seeds) ===")
    strat_names = list(per[0]["strategies"].keys())
    means = {}
    for name in strat_names:
        means[name] = {
            m: statistics.mean([p["strategies"][name][m] for p in per])
            for m in ("cagr", "sharpe", "sortino", "calmar", "max_drawdown", "expected_utility", "vol")
        }
    print(f"{'strategy':<14}{'CAGR':>9}{'Sharpe':>8}{'Sortino':>9}{'Calmar':>8}{'MaxDD':>8}{'EU':>9}{'vol':>8}")
    for name in sorted(strat_names, key=lambda n: -means[n]["sharpe"]):
        m = means[name]
        print(f"{name:<14}{m['cagr']:>9.4f}{m['sharpe']:>8.3f}{m['sortino']:>9.3f}"
              f"{m['calmar']:>8.3f}{m['max_drawdown']:>8.3f}{m['expected_utility']:>9.5f}{m['vol']:>8.3f}")

    # paired bootstrap: Athena vs each benchmark on per-seed Sharpe & CAGR
    print("\n=== ATHENA vs BENCHMARK — paired bootstrap (per-seed Sharpe) ===")
    ath_sh = [p["strategies"]["Athena"]["sharpe"] for p in per]
    ath_cagr = [p["strategies"]["Athena"]["cagr"] for p in per]
    print(f"{'benchmark':<14}{'dSharpe':>9}{'95%CI':>22}{'p':>8}{'win%':>7}")
    for name in strat_names:
        if name == "Athena":
            continue
        b_sh = [p["strategies"][name]["sharpe"] for p in per]
        point, lo, hi, pval = bootstrap_diff_ci(ath_sh, b_sh, seed=7)
        winrate = statistics.mean([1.0 if a > b else 0.0 for a, b in zip(ath_sh, b_sh, strict=False)])
        print(f"{name:<14}{point:>+9.3f}  [{lo:+.3f},{hi:+.3f}]{'':>4}{pval:>8.4f}{winrate*100:>6.0f}%")

    print("\n=== ATHENA vs BENCHMARK — paired bootstrap (per-seed CAGR) ===")
    print(f"{'benchmark':<14}{'dCAGR':>9}{'95%CI':>22}{'p':>8}{'win%':>7}")
    for name in strat_names:
        if name == "Athena":
            continue
        b = [p["strategies"][name]["cagr"] for p in per]
        point, lo, hi, pval = bootstrap_diff_ci(ath_cagr, b, seed=7)
        winrate = statistics.mean([1.0 if a > bb else 0.0 for a, bb in zip(ath_cagr, b, strict=False)])
        print(f"{name:<14}{point:>+9.4f}  [{lo:+.4f},{hi:+.4f}]{'':>3}{pval:>8.4f}{winrate*100:>6.0f}%")

    # --- confidence distribution ---
    print("\n=== CONFIDENCE DISTRIBUTION (mean over seeds) ===")
    for k in ("mean", "p25", "p50", "p75", "min", "max"):
        xs = [p["confidence_dist"][k] for p in per]
        print(f"  conf_{k:5} = {statistics.mean(xs):.4f}")


if __name__ == "__main__":
    main()
