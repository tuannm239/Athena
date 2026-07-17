# ATHENA — Performance Benchmarks (Phase 2, Module 8)

Generated 2026-07-16 with `uv run python scripts/benchmark.py
--iterations 200` on the CI-class container (Python 3.13, single
process). Workloads are deterministic; re-run the script to compare a
commit against this baseline.

## Results

| Benchmark | Iterations | P50 (ms) | P95 (ms) | P99 (ms) | Throughput (ops/s) | Peak mem (KB) |
|---|---|---|---|---|---|---|
| DSL compile (3-rule ruleset, full pipeline) | 200 | 1.695 | 2.138 | 2.895 | 570.8 | 59.2 |
| Decision-graph evaluation (kernel hot path) | 2000 | 0.032 | 0.052 | 0.070 | 28 186 | 61.8 |
| Probability engine (30 evidence, RFC-0026) | 200 | 0.805 | 1.184 | 1.368 | 1 177.9 | 14.2 |
| KG impacts (1 000 companies, 20 industries) | 200 | 0.085 | 0.125 | 0.178 | 10 660 | 5.6 |
| KG traversal depth 3 | 200 | 0.086 | 0.111 | 0.121 | 11 024 | 5.0 |
| Backtest 20 tickers × 252 days, weekly | 10 | 62.267 | 64.388 | 64.388 | 16.1 | 224.1 |

Application startup (cold `create_app` factory incl. container,
routers, metrics registry, schema create on SQLite): **45.9 ms**.

## Assessment against targets

| Path | Target | Measured | Verdict |
|---|---|---|---|
| Rule evaluation inside the kernel | < 1 ms P95 (interactive decision evaluation) | 0.052 ms P95 | ✅ ~19× headroom |
| Ruleset compilation | < 50 ms P95 (compile-on-save UX) | 2.138 ms P95 | ✅ |
| Probability update per decision | < 10 ms P95 (SPEC-04 pipeline step) | 1.184 ms P95 | ✅ |
| KG reasoning query | < 5 ms P95 at 1k-node scale | 0.125 ms P95 | ✅ (revisit at 100k nodes) |
| One year × 20 tickers backtest | < 1 s (research iteration loop) | 64 ms P95 | ✅ ~15× headroom |
| API process startup | < 2 s (rolling deploys, autoscaling) | 46 ms | ✅ |

## Notes

- All numeric work is `Decimal`-based by constitution; the measured
  headroom shows the correctness choice is affordable at current scale.
- Peak memory per operation stays under 250 KB in every benchmark; the
  backtest dominates (price map + equity curves), scaling linearly with
  tickers × days.
- The kernel hot path (graph evaluation) sustains ~28k evaluations/s
  single-threaded — a full 1 000-ticker universe scan per rebalance
  costs ~35 ms.
- Watchpoints for the next revision: KG traversal at ≥100k nodes
  (SQL-side traversal or adjacency caching per ADR-0007), and the
  backtest engine when intraday bars land (vectorize the return loop
  with Polars).
