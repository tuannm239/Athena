"""Replay Athena decisions over the synthetic VN market and record the
decision-vs-outcome record used by W2 (validation), W3 (calibration),
W4 (feature importance) and W5 (drift).

Uses the REAL RFC-0026 ProbabilityEngine. For each monthly rebalance and
each company, observable factors (quality/value/momentum) become Evidence;
the engine produces a posterior P(outperform market over the next month).
Ground truth = did the company out-return the market over that month.
Deterministic in the market seed.
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

import research.vn_market as vm  # noqa: E402
from decision_kernel.domain.evidence import Evidence, EvidenceDirection  # noqa: E402
from probability.domain.engine import ProbabilityEngine  # noqa: E402
from shared_kernel.probability import Probability, Reliability  # noqa: E402

HORIZON = 21  # trading days (~1 month) forward
STEP = 21  # monthly rebalance
AS_OF = datetime(2026, 1, 1, tzinfo=timezone.utc)
_ENGINE = ProbabilityEngine()


def _clip(x: float, lo: float = 0.02, hi: float = 0.98) -> float:
    return max(lo, min(hi, x))


def _evidence(q: float, v: float, m: float, as_of: datetime) -> tuple[Evidence, ...]:
    """One evidence item per observable factor; direction and strength
    encode the factor. Uses the ADR-0006 explicit-direction model."""
    out = []
    for name, f in (("quality", q), ("value", v), ("momentum", m)):
        direction = EvidenceDirection.SUPPORTING if f >= 0.5 else EvidenceDirection.CONTRADICTING
        strength = _clip(abs(f - 0.5) * 2)
        out.append(
            Evidence(
                source=f"factor:{name}",
                category="factor",
                reliability=Reliability(Decimal(str(round(strength, 4)))),
                direction=direction,
                explanation=f"{name}={f:.3f}",
                timestamp=as_of - timedelta(days=1),
            )
        )
    return tuple(out)


def posterior(q: float, v: float, m: float, as_of: datetime = AS_OF) -> tuple[float, float]:
    rep = _ENGINE.evaluate(
        hypothesis="outperform",
        prior=Probability(Decimal("0.5")),
        evidence=_evidence(q, v, m, as_of),
        as_of=as_of,
        expected_return=Decimal("0.05"),
        expected_drawdown=Decimal("0.03"),
        assumptions=(),
    )
    return float(rep.posterior.value), float(rep.confidence.value)


@dataclass
class DecisionRecord:
    month: int
    day: int
    ticker: str
    sector: str
    regime: str
    quality: float
    value: float
    momentum: float
    posterior: float
    confidence: float
    fwd_return: float
    mkt_fwd_return: float
    outperformed: int  # 1 if fwd_return > mkt_fwd_return


def replay(panel: vm.MarketPanel) -> list[DecisionRecord]:
    records: list[DecisionRecord] = []
    n = panel.n_days
    month = 0
    for day in range(0, n - HORIZON, STEP):
        as_of = AS_OF + timedelta(days=day)
        mkt_fwd = panel.market[day + HORIZON] / panel.market[day] - 1
        for c in panel.companies:
            q = panel.quality[c.ticker][day]
            v = panel.value[c.ticker][day]
            mo = panel.momentum[c.ticker][day]
            p, conf = posterior(q, v, mo, as_of)
            fwd = panel.prices[c.ticker][day + HORIZON] / panel.prices[c.ticker][day] - 1
            records.append(
                DecisionRecord(
                    month=month,
                    day=day,
                    ticker=c.ticker,
                    sector=c.sector,
                    regime=panel.regimes[day],
                    quality=q,
                    value=v,
                    momentum=mo,
                    posterior=p,
                    confidence=conf,
                    fwd_return=fwd,
                    mkt_fwd_return=mkt_fwd,
                    outperformed=1 if fwd > mkt_fwd else 0,
                )
            )
        month += 1
    return records


def main() -> None:
    import time

    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 20260718
    t0 = time.perf_counter()
    panel = vm.generate_market(seed=seed)
    records = replay(panel)
    elapsed = time.perf_counter() - t0
    out = (
        Path(__file__).resolve().parents[1]
        / "research"
        / "experiments"
        / f"decisions_seed{seed}.json"
    )
    out.write_text(json.dumps([asdict(r) for r in records]))
    print(
        f"seed={seed} decisions={len(records)} months={records[-1].month + 1} "
        f"elapsed={elapsed:.1f}s -> {out.name}"
    )


if __name__ == "__main__":
    main()
