"""W7 Human Review — SIMULATED override overlay.

No real human-reviewer logs exist in this environment. This models a
modestly-skilled analyst reviewing each Athena decision, to build the
override-tracking framework and quantify the net effect of overrides.
Assumptions are explicit; re-run against real reviewer logs when
available. Deterministic in seed.
"""

from __future__ import annotations

import random
import statistics
from collections import Counter

import research.vn_market as vm
from research.replay_decisions import replay

# Simulated analyst skill: probability their independent call is correct.
# 0.50 = no skill; we model a slightly-skilled analyst.
HUMAN_SKILL = 0.51


def simulate(seed: int) -> dict:
    panel = vm.generate_market(seed=seed)
    records = replay(panel)
    rng = random.Random(seed + 99)

    conf_all = sorted(r.confidence for r in records)
    conf_p25 = conf_all[len(conf_all) // 4]

    reasons = Counter()
    n = len(records)
    ath_correct = human_correct = final_correct = 0
    ath_ret = human_ret = final_ret = 0.0
    overrides = 0

    for r in records:
        athena_long = r.posterior > 0.5
        # --- human independently forms a call ---
        # modestly-skilled: matches truth with prob HUMAN_SKILL, else opposite
        truth_long = r.outperformed == 1
        human_long = truth_long if rng.random() < HUMAN_SKILL else (not truth_long)

        # --- override policy (reasons) ---
        override = False
        if r.confidence < conf_p25:
            override = True
            reasons["low_confidence"] += 1
        elif r.regime == "CONTRACTION" and athena_long:
            # risk-averse: veto longs in contraction
            human_long = False
            override = True
            reasons["risk_aversion_contraction"] += 1
        elif r.value < 0.3 and r.momentum > 0.7 and athena_long:
            # contrarian-value: distrust momentum-chasing
            human_long = False
            override = True
            reasons["contrarian_value"] += 1

        final_long = human_long if override else athena_long
        if override:
            overrides += 1

        # scoring: "long" is correct if the name outperformed
        edge = r.fwd_return - r.mkt_fwd_return
        if athena_long == truth_long:
            ath_correct += 1
        if human_long == truth_long:
            human_correct += 1
        if final_long == truth_long:
            final_correct += 1
        # return contribution: taking the long earns edge; passing earns 0
        ath_ret += edge if athena_long else 0.0
        human_ret += edge if human_long else 0.0
        final_ret += edge if final_long else 0.0

    return {
        "seed": seed,
        "n": n,
        "override_rate": overrides / n,
        "reasons": dict(reasons),
        "athena_acc": ath_correct / n,
        "human_acc": human_correct / n,
        "final_acc": final_correct / n,
        "athena_ret": ath_ret / n,
        "human_ret": human_ret / n,
        "final_ret": final_ret / n,
    }


def main() -> None:
    seeds = [20260718 + i for i in range(5)]
    rows = [simulate(s) for s in seeds]

    def m(k):
        return statistics.mean([r[k] for r in rows])

    print("=== HUMAN REVIEW OVERRIDE SIMULATION (5 seeds, analyst skill=0.51) ===")
    print(f"override_rate       {m('override_rate') * 100:.1f}%")
    reasons = Counter()
    for r in rows:
        reasons.update(r["reasons"])
    total = sum(reasons.values())
    print("override reasons:")
    for reason, c in reasons.most_common():
        print(f"   {reason:28} {c / total * 100:.1f}%")
    print(f"\n{'policy':<22}{'accuracy':>10}{'mean edge/decision':>20}")
    print(f"{'Athena alone':<22}{m('athena_acc'):>10.4f}{m('athena_ret'):>20.5f}")
    print(f"{'Human alone':<22}{m('human_acc'):>10.4f}{m('human_ret'):>20.5f}")
    print(f"{'Athena+Human override':<22}{m('final_acc'):>10.4f}{m('final_ret'):>20.5f}")
    print(f"\noverride net effect on accuracy: {(m('final_acc') - m('athena_acc')) * 100:+.2f} pp")
    print(
        f"override net effect on edge:     {(m('final_ret') - m('athena_ret')):+.5f} per decision"
    )


if __name__ == "__main__":
    main()
