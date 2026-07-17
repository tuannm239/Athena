"""Phase 2 Module 8 — the benchmark suite stays runnable."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "benchmark.py"


def test_benchmark_suite_runs_and_reports() -> None:
    spec = importlib.util.spec_from_file_location("athena_benchmark", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses resolve annotations via sys.modules
    spec.loader.exec_module(module)

    results, startup_ms = module.run(iterations=5)
    names = {r.name for r in results}
    assert {
        "dsl_compile_3_rules",
        "dsl_evaluate_graph",
        "probability_30_evidence",
        "kg_impacts_1000_nodes",
        "kg_traverse_depth3",
        "backtest_20x252_weekly",
    } <= names
    for result in results:
        assert result.p50_ms <= result.p95_ms <= result.p99_ms
        assert result.throughput_per_s > 0
        assert result.peak_memory_kb > 0
    assert startup_ms > 0
