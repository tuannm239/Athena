"""ATHENA performance benchmarks (Phase 2, Module 8).

Measures the four hot paths — DSL compiler, probability engine,
knowledge-graph traversal, backtest engine — plus application startup:
P50/P95/P99 latency, throughput, peak memory (tracemalloc). Synthetic
workloads are deterministic (fixed seeds/sizes) so runs are comparable
across commits.

Usage:
    uv run python scripts/benchmark.py [--iterations 200] [--json out.json]

The committed baseline lives in docs/BENCHMARKS.md.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
import tracemalloc
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from backtest.domain.simulator import (  # noqa: E402
    BacktestConfig,
    BacktestEngine,
    DailyBar,
    SimulationMode,
)
from decision_kernel.domain.evidence import Evidence, EvidenceDirection  # noqa: E402
from dsl.domain.compiler import compile_rules  # noqa: E402
from dsl.domain.evaluator import FactValue  # noqa: E402
from dsl.domain.evaluator import evaluate as evaluate_graph  # noqa: E402
from knowledge.domain.graph import Edge, GraphSnapshot, Node, NodeType, RelationType  # noqa: E402
from knowledge.domain.traversal import find_impacts, traverse  # noqa: E402
from probability.domain.engine import ProbabilityEngine  # noqa: E402
from shared_kernel.probability import Probability, Reliability  # noqa: E402

RULESET = """
RULE HighQualityCompounder
VERSION "1.0"
PRIORITY 100
WHEN
    Market.Regime == Expansion
    AND Company.ROIC > 20
    AND Company.RevenueGrowth > 15
    AND Company.DebtToEquity < 0.50
THEN
    PROBABILITY += 0.08
    CONFIDENCE += 0.05
    UTILITY += 0.12
    RISK -= 0.04
    TAG "Quality"
EXPLAIN "High quality compounder during expansion."

RULE ContractionCaution
PRIORITY 200
WHEN Market.Regime == Contraction
THEN
    PROBABILITY -= 0.10
    RISK += 0.10
    TAG "Defensive"
EXPLAIN "Reduce conviction during contraction."

RULE ExpensiveValuation
WHEN Company.PEPercentile > 90
THEN
    UTILITY -= 0.05
    TAG "Expensive"
EXPLAIN "Valuation stretched versus history."
"""

FACTS: dict[str, FactValue] = {
    "Market.Regime": "Expansion",
    "Company.ROIC": Decimal(25),
    "Company.RevenueGrowth": Decimal(18),
    "Company.DebtToEquity": Decimal("0.3"),
    "Company.PEPercentile": Decimal(95),
}

AS_OF = datetime(2026, 7, 16, tzinfo=timezone.utc)


@dataclass(frozen=True)
class BenchResult:
    name: str
    iterations: int
    p50_ms: float
    p95_ms: float
    p99_ms: float
    mean_ms: float
    throughput_per_s: float
    peak_memory_kb: float


def bench(name: str, fn: Callable[[], object], iterations: int) -> BenchResult:
    fn()  # warm-up (imports, caches)
    tracemalloc.start()
    samples: list[float] = []
    started = time.perf_counter()
    for _ in range(iterations):
        t0 = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - t0) * 1000)
    elapsed = time.perf_counter() - started
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    ordered = sorted(samples)

    def pct(p: float) -> float:
        return ordered[min(len(ordered) - 1, int(len(ordered) * p))]

    return BenchResult(
        name=name,
        iterations=iterations,
        p50_ms=round(pct(0.50), 3),
        p95_ms=round(pct(0.95), 3),
        p99_ms=round(pct(0.99), 3),
        mean_ms=round(statistics.fmean(samples), 3),
        throughput_per_s=round(iterations / elapsed, 1),
        peak_memory_kb=round(peak / 1024, 1),
    )


def _evidence(count: int) -> tuple[Evidence, ...]:
    directions = (
        EvidenceDirection.SUPPORTING,
        EvidenceDirection.CONTRADICTING,
        EvidenceDirection.NEUTRAL,
    )
    return tuple(
        Evidence(
            source=f"report:{i}",
            category="financial",
            reliability=Reliability(Decimal("0.8")),
            direction=directions[i % 3],
            explanation=f"evidence item {i}",
            timestamp=AS_OF - timedelta(days=i * 10),
        )
        for i in range(count)
    )


def _graph(companies: int) -> GraphSnapshot:
    nodes: dict[str, Node] = {"sector.X": Node("sector.X", NodeType.SECTOR, "X")}
    edges: list[Edge] = []
    for i in range(companies):
        company = f"company.C{i}"
        industry = f"industry.I{i % 20}"
        nodes[company] = Node(company, NodeType.COMPANY, f"C{i}")
        if industry not in nodes:
            nodes[industry] = Node(industry, NodeType.INDUSTRY, industry)
            edges.append(Edge(industry, RelationType.BELONGS_TO, "sector.X", "bench"))
        edges.append(Edge(company, RelationType.BELONGS_TO, industry, "bench"))
    return GraphSnapshot(version=1, nodes=nodes, edges=tuple(edges))


def _price_series(tickers: int, days: int) -> dict[str, tuple[DailyBar, ...]]:
    start = date(2024, 1, 1)
    series: dict[str, tuple[DailyBar, ...]] = {}
    for t in range(tickers):
        price = Decimal(100 + t)
        bars = []
        for d in range(days):
            price = price * (Decimal(1) + Decimal((t + d) % 7 - 3) / Decimal(1000))
            bars.append(DailyBar(day=start + timedelta(days=d), close=price))
        series[f"T{t}"] = tuple(bars)
    return series


def run(iterations: int) -> tuple[list[BenchResult], float]:
    results: list[BenchResult] = []

    # 1. DSL compiler: full pipeline source -> compiled ruleset.
    results.append(bench("dsl_compile_3_rules", lambda: compile_rules(RULESET), iterations))

    # 2. Graph evaluation (kernel hot path): compiled once, evaluated many.
    compiled = compile_rules(RULESET)
    results.append(
        bench(
            "dsl_evaluate_graph",
            lambda: evaluate_graph(compiled.graph, FACTS),
            iterations * 10,
        )
    )

    # 3. Probability engine: RFC-0026 pipeline over 30 evidence items.
    evidence = _evidence(30)
    engine = ProbabilityEngine()
    results.append(
        bench(
            "probability_30_evidence",
            lambda: engine.evaluate(
                hypothesis="H",
                prior=Probability(Decimal("0.5")),
                evidence=evidence,
                as_of=AS_OF,
                expected_return=Decimal("0.2"),
                expected_drawdown=Decimal("0.1"),
                assumptions=(),
            ),
            iterations,
        )
    )

    # 4. Knowledge graph: 1000 companies, downstream impacts + BFS.
    snapshot = _graph(1000)
    results.append(
        bench("kg_impacts_1000_nodes", lambda: find_impacts(snapshot, "company.C0"), iterations)
    )
    results.append(
        bench(
            "kg_traverse_depth3",
            lambda: traverse(snapshot, "company.C0", max_depth=3),
            iterations,
        )
    )

    # 5. Backtest: 20 tickers x 252 days, weekly rebalancing.
    prices = _price_series(20, 252)
    config = BacktestConfig(ruleset=compiled, mode=SimulationMode.WEEKLY)
    engine_bt = BacktestEngine(config=config, facts=lambda _d, _t: FACTS)
    results.append(
        bench(
            "backtest_20x252_weekly",
            lambda: engine_bt.run(prices),
            max(iterations // 20, 5),
        )
    )

    # 6. Startup: full app factory over SQLite (routers, container, metrics).
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from api.main import create_app
    from infrastructure.config import Settings
    from infrastructure.db.base import Base

    def startup() -> object:
        engine = create_engine(
            "sqlite+pysqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(engine)
        return create_app(
            settings=Settings(
                database_url="sqlite://",
                redis_url="redis://localhost:1/0",
                duckdb_dir="data/snapshots",
                jwt_secret="benchmark-secret",
                access_token_ttl_seconds=900,
                refresh_token_ttl_seconds=3600,
            ),
            session_factory=sessionmaker(bind=engine, expire_on_commit=False),
        )

    t0 = time.perf_counter()
    startup()
    startup_ms = (time.perf_counter() - t0) * 1000
    return results, round(startup_ms, 1)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=200)
    parser.add_argument("--json", type=Path, default=None)
    args = parser.parse_args()

    results, startup_ms = run(args.iterations)

    header = (
        f"{'benchmark':<28}{'iters':>7}{'p50 ms':>9}{'p95 ms':>9}"
        f"{'p99 ms':>9}{'ops/s':>10}{'peak KB':>10}"
    )
    print(header)
    print("-" * len(header))
    for r in results:
        print(
            f"{r.name:<28}{r.iterations:>7}{r.p50_ms:>9}{r.p95_ms:>9}"
            f"{r.p99_ms:>9}{r.throughput_per_s:>10}{r.peak_memory_kb:>10}"
        )
    print(f"\napp startup (cold factory): {startup_ms} ms")

    if args.json is not None:
        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "startup_ms": startup_ms,
            "results": [asdict(r) for r in results],
        }
        args.json.write_text(json.dumps(payload, indent=2))
        print(f"written: {args.json}")


if __name__ == "__main__":
    main()
