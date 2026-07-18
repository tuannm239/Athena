"""Consolidated Phase 4 research study — computes every metric used by
workstreams W2–W8 from the real Athena decision replay over the seeded
synthetic VN market. Pure-Python statistics (no numpy/scipy).

Run:  python -m research.study            # single seed, prints summary
      python -m research.study --seeds 20 # multi-seed, writes study.json
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import time
from collections import defaultdict
from pathlib import Path

import research.vn_market as vm
from research.replay_decisions import DecisionRecord, posterior, replay

TRADING_DAYS = 252
BASE_SEED = 20260718


# ------------------------- generic statistics -------------------------------
def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def pearson(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    if n < 2:
        return 0.0
    mx, my = _mean(xs), _mean(ys)
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=False))
    vx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    vy = math.sqrt(sum((y - my) ** 2 for y in ys))
    return cov / (vx * vy) if vx and vy else 0.0


def mutual_information(feature: list[float], label: list[int], bins: int = 5) -> float:
    """MI between a continuous feature (binned) and a binary label, in nats."""
    n = len(feature)

    def binof(x: float) -> int:
        return min(bins - 1, max(0, int(x * bins)))

    joint: dict[tuple[int, int], int] = defaultdict(int)
    px: dict[int, int] = defaultdict(int)
    py: dict[int, int] = defaultdict(int)
    for f, y in zip(feature, label, strict=False):
        b = binof(f)
        joint[(b, y)] += 1
        px[b] += 1
        py[y] += 1
    mi = 0.0
    for (b, y), c in joint.items():
        pxy = c / n
        mi += pxy * math.log(pxy / ((px[b] / n) * (py[y] / n)))
    return mi


def population_stability_index(a: list[float], b: list[float], bins: int = 10) -> float:
    """PSI between two samples of a variable in [0,1]."""
    def hist(xs: list[float]) -> list[float]:
        h = [0] * bins
        for x in xs:
            h[min(bins - 1, max(0, int(x * bins)))] += 1
        return [c / len(xs) for c in h]

    ha, hb = hist(a), hist(b)
    psi = 0.0
    for pa, pb in zip(ha, hb, strict=False):
        pa = max(pa, 1e-6)
        pb = max(pb, 1e-6)
        psi += (pa - pb) * math.log(pa / pb)
    return psi


def brier(preds: list[float], labels: list[int]) -> float:
    return sum((p - y) ** 2 for p, y in zip(preds, labels, strict=False)) / len(preds)


def calibration_bins(preds: list[float], labels: list[int], bins: int = 10):
    b = [[] for _ in range(bins)]
    for p, y in zip(preds, labels, strict=False):
        b[min(bins - 1, int(p * bins))].append((p, y))
    rows = []
    ece = 0.0
    n = len(preds)
    for i, grp in enumerate(b):
        if not grp:
            rows.append((i / bins, 0, None, None))
            continue
        mp = _mean([p for p, _ in grp])
        hr = _mean([y for _, y in grp])
        ece += (len(grp) / n) * abs(mp - hr)
        rows.append((i / bins, len(grp), mp, hr))
    return rows, ece


# ------------------------- portfolio construction ---------------------------
def chain(monthly_returns: list[float]) -> list[float]:
    eq = [1.0]
    for r in monthly_returns:
        eq.append(eq[-1] * (1 + r))
    return eq


def port_metrics(monthly_returns: list[float]) -> dict:
    eq = chain(monthly_returns)
    n_years = len(monthly_returns) / 12
    cagr = eq[-1] ** (1 / n_years) - 1 if eq[-1] > 0 else -1.0
    mu = _mean(monthly_returns)
    sd = statistics.pstdev(monthly_returns) if len(monthly_returns) > 1 else 0.0
    sharpe = (mu / sd * math.sqrt(12)) if sd else 0.0
    downs = [r for r in monthly_returns if r < 0]
    dd = math.sqrt(sum(r * r for r in downs) / len(monthly_returns)) if downs else 0.0
    sortino = (mu / dd * math.sqrt(12)) if dd else 0.0
    peak, mdd = eq[0], 0.0
    for x in eq:
        peak = max(peak, x)
        mdd = min(mdd, x / peak - 1)
    calmar = (cagr / abs(mdd)) if mdd else 0.0
    # expected utility: mean log-wealth growth (risk-averse, SPEC-11 spirit)
    eu = _mean([math.log(1 + r) for r in monthly_returns if r > -1])
    return {
        "cagr": cagr, "sharpe": sharpe, "sortino": sortino, "calmar": calmar,
        "max_drawdown": mdd, "expected_utility": eu, "vol": sd * math.sqrt(12),
        "final_mult": eq[-1], "months": len(monthly_returns),
    }


def _by_month(records: list[DecisionRecord]) -> dict[int, list[DecisionRecord]]:
    m: dict[int, list[DecisionRecord]] = defaultdict(list)
    for r in records:
        m[r.month].append(r)
    return m


def _select_top(recs: list[DecisionRecord], key, frac: float) -> list[DecisionRecord]:
    k = max(1, int(len(recs) * frac))
    return sorted(recs, key=key, reverse=True)[:k]


def strategy_returns(records: list[DecisionRecord], vn30: set[str], frac: float = 0.2) -> dict:
    """Monthly returns for each strategy (equal-weight of selected names)."""
    months = sorted(_by_month(records))
    bm = _by_month(records)
    series: dict[str, list[float]] = defaultdict(list)
    for mo in months:
        recs = bm[mo]
        mkt = recs[0].mkt_fwd_return
        # benchmarks
        series["VNINDEX"].append(mkt)
        series["ETF_passive"].append(mkt - 0.001)  # index fund minus fee
        series["EqualWeight"].append(_mean([r.fwd_return for r in recs]))
        vn30r = [r.fwd_return for r in recs if r.ticker in vn30]
        series["VN30"].append(_mean(vn30r) if vn30r else mkt)
        # factor strategies (top quintile by single factor)
        series["Value"].append(_mean([r.fwd_return for r in _select_top(recs, lambda r: r.value, frac)]))
        series["Momentum"].append(_mean([r.fwd_return for r in _select_top(recs, lambda r: r.momentum, frac)]))
        series["Quality"].append(_mean([r.fwd_return for r in _select_top(recs, lambda r: r.quality, frac)]))
        series["Growth"].append(_mean([r.fwd_return for r in _select_top(recs, lambda r: r.momentum + r.quality, frac)]))
        # Athena: top quintile by posterior probability
        series["Athena"].append(_mean([r.fwd_return for r in _select_top(recs, lambda r: r.posterior, frac)]))
    return series


# ------------------------- per-seed study -----------------------------------
def study_seed(seed: int) -> dict:
    panel = vm.generate_market(seed=seed)
    records = replay(panel)
    vn30 = set(panel.vn30)
    preds = [r.posterior for r in records]
    labels = [r.outperformed for r in records]

    # W2/W3 calibration + accuracy
    rows, ece = calibration_bins(preds, labels)
    br = brier(preds, labels)
    acc = _mean([1.0 if (p > 0.5) == bool(y) else 0.0 for p, y in zip(preds, labels, strict=False)])
    # AUC (rank-based, Mann-Whitney)
    pos = sorted(p for p, y in zip(preds, labels, strict=False) if y == 1)
    neg = [p for p, y in zip(preds, labels, strict=False) if y == 0]
    if pos and neg:
        allp = sorted((p, y) for p, y in zip(preds, labels, strict=False))
        rank = {}
        i = 0
        while i < len(allp):
            j = i
            while j < len(allp) and allp[j][0] == allp[i][0]:
                j += 1
            avg = (i + j - 1) / 2 + 1
            for k in range(i, j):
                rank[k] = avg
            i = j
        sum_pos = sum(rank[idx] for idx, (_, y) in enumerate(allp) if y == 1)
        n_pos, n_neg = len(pos), len(neg)
        auc = (sum_pos - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg)
    else:
        auc = 0.5

    # EU separation: mean realized outperf return for positive vs negative decisions
    pos_r = [r.fwd_return - r.mkt_fwd_return for r in records if r.posterior > 0.5]
    neg_r = [r.fwd_return - r.mkt_fwd_return for r in records if r.posterior <= 0.5]
    eu_spread = _mean(pos_r) - _mean(neg_r)

    # Stability: posterior drift under +/-eps feature perturbation (sample)
    import random as _r
    rr = _r.Random(seed)
    sample = rr.sample(records, min(1000, len(records)))
    flips, drift = 0, 0.0
    for rec in sample:
        p2, _ = posterior(min(1, rec.quality + 0.02), rec.value, rec.momentum)
        drift += abs(p2 - rec.posterior)
        if (p2 > 0.5) != (rec.posterior > 0.5):
            flips += 1
    stability_flip = flips / len(sample)
    stability_drift = drift / len(sample)

    # W4 feature importance
    feats = {"quality": [r.quality for r in records],
             "value": [r.value for r in records],
             "momentum": [r.momentum for r in records]}
    corr = {k: pearson(v, [float(y) for y in labels]) for k, v in feats.items()}
    mi = {k: mutual_information(v, labels) for k, v in feats.items()}
    # permutation importance: shuffle a feature, recompute accuracy drop
    base_acc = acc
    perm_imp = {}
    for k in feats:
        rr2 = _r.Random(seed + 1)
        shuffled = feats[k][:]
        rr2.shuffle(shuffled)
        # recompute posterior with the shuffled feature
        drop_correct = 0
        cnt = 0
        idxs = rr2.sample(range(len(records)), min(3000, len(records)))
        for idx in idxs:
            rec = records[idx]
            qq = shuffled[idx] if k == "quality" else rec.quality
            vv = shuffled[idx] if k == "value" else rec.value
            mm = shuffled[idx] if k == "momentum" else rec.momentum
            p2, _ = posterior(qq, vv, mm)
            drop_correct += 1.0 if (p2 > 0.5) == bool(rec.outperformed) else 0.0
            cnt += 1
        perm_acc = drop_correct / cnt
        perm_imp[k] = base_acc - perm_acc
    # exact Shapley on the 3-feature accuracy game (2^3 coalitions)
    shap = shapley_features(records, seed)

    # W5 drift: first third vs last third of the timeline
    months = sorted({r.month for r in records})
    third = len(months) // 3
    early = set(months[:third])
    late = set(months[-third:])
    e_recs = [r for r in records if r.month in early]
    l_recs = [r for r in records if r.month in late]
    drift_metrics = {
        "posterior_psi": population_stability_index([r.posterior for r in e_recs], [r.posterior for r in l_recs]),
        "confidence_psi": population_stability_index([r.confidence for r in e_recs], [r.confidence for r in l_recs]),
        "quality_psi": population_stability_index([r.quality for r in e_recs], [r.quality for r in l_recs]),
        "decision_rate_early": _mean([1.0 if r.posterior > 0.5 else 0.0 for r in e_recs]),
        "decision_rate_late": _mean([1.0 if r.posterior > 0.5 else 0.0 for r in l_recs]),
        "accuracy_early": _mean([1.0 if (r.posterior > 0.5) == bool(r.outperformed) else 0.0 for r in e_recs]),
        "accuracy_late": _mean([1.0 if (r.posterior > 0.5) == bool(r.outperformed) else 0.0 for r in l_recs]),
    }

    # W6/W8 strategies
    strat = strategy_returns(records, vn30)
    strat_metrics = {name: port_metrics(rets) for name, rets in strat.items()}

    # confidence distribution
    confs = [r.confidence for r in records]
    conf_dist = {
        "mean": _mean(confs), "min": min(confs), "max": max(confs),
        "p25": statistics.quantiles(confs, n=4)[0],
        "p50": statistics.median(confs),
        "p75": statistics.quantiles(confs, n=4)[2],
    }

    return {
        "seed": seed, "n_decisions": len(records), "n_months": len(months),
        "base_rate_outperform": _mean([float(y) for y in labels]),
        "accuracy": acc, "auc": auc, "brier": br, "ece": ece,
        "eu_spread": eu_spread, "stability_flip": stability_flip,
        "stability_drift": stability_drift,
        "calibration_rows": rows, "confidence_dist": conf_dist,
        "correlation": corr, "mutual_information": mi,
        "permutation_importance": perm_imp, "shapley": shap,
        "drift": drift_metrics, "strategies": strat_metrics,
        "strategy_monthly": {k: v for k, v in strat.items()},
    }


def shapley_features(records: list[DecisionRecord], seed: int) -> dict:
    """Exact Shapley values for the 3 features on the decision-accuracy
    game (all 2^3 coalitions). Absent features are set to the neutral 0.5.
    This IS SHAP, computed exactly on a small feature set (no library)."""
    import random as _r
    rr = _r.Random(seed + 7)
    idxs = rr.sample(range(len(records)), min(2000, len(records)))
    feats = ("quality", "value", "momentum")

    def acc_for(coalition: frozenset) -> float:
        correct = 0
        for idx in idxs:
            rec = records[idx]
            q = rec.quality if "quality" in coalition else 0.5
            v = rec.value if "value" in coalition else 0.5
            m = rec.momentum if "momentum" in coalition else 0.5
            p2, _ = posterior(q, v, m)
            correct += 1.0 if (p2 > 0.5) == bool(rec.outperformed) else 0.0
        return correct / len(idxs)

    from itertools import combinations
    cache: dict[frozenset, float] = {}
    for k in range(4):
        for combo in combinations(feats, k):
            cache[frozenset(combo)] = acc_for(frozenset(combo))
    shap = {}
    import math as _m
    for f in feats:
        val = 0.0
        others = [x for x in feats if x != f]
        for k in range(len(others) + 1):
            for combo in combinations(others, k):
                S = frozenset(combo)
                w = _m.factorial(k) * _m.factorial(len(feats) - k - 1) / _m.factorial(len(feats))
                val += w * (cache[S | {f}] - cache[S])
        shap[f] = val
    return shap


# ------------------------- multi-seed driver --------------------------------
def bootstrap_diff_ci(a: list[float], b: list[float], iters: int = 5000, seed: int = 1):
    """Paired bootstrap CI for mean(a-b)."""
    import random as _r
    rr = _r.Random(seed)
    diffs = [x - y for x, y in zip(a, b, strict=False)]
    n = len(diffs)
    means = []
    for _ in range(iters):
        s = [diffs[rr.randrange(n)] for _ in range(n)]
        means.append(sum(s) / n)
    means.sort()
    lo = means[int(0.025 * iters)]
    hi = means[int(0.975 * iters)]
    point = sum(diffs) / n
    # two-sided p-value via sign of CI (fraction of bootstrap means <=0 or >=0)
    p_pos = sum(1 for m in means if m <= 0) / iters
    pval = 2 * min(p_pos, 1 - p_pos)
    return point, lo, hi, pval


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=1)
    args = ap.parse_args()
    t0 = time.perf_counter()
    seeds = [BASE_SEED + i for i in range(args.seeds)]
    per_seed = []
    for s in seeds:
        r = study_seed(s)
        per_seed.append(r)
        print(f"seed={s} acc={r['accuracy']:.4f} auc={r['auc']:.4f} ece={r['ece']:.4f} "
              f"brier={r['brier']:.4f} Athena_sharpe={r['strategies']['Athena']['sharpe']:.3f} "
              f"VNINDEX_sharpe={r['strategies']['VNINDEX']['sharpe']:.3f}")
    elapsed = time.perf_counter() - t0

    out = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "seeds": seeds, "n_seeds": len(seeds), "elapsed_s": round(elapsed, 1),
        "per_seed": per_seed,
    }
    path = Path(__file__).resolve().parents[1] / "research" / "experiments" / "study.json"
    path.write_text(json.dumps(out, indent=2))
    print(f"\n{len(seeds)} seeds in {elapsed:.1f}s -> {path}")


if __name__ == "__main__":
    main()
