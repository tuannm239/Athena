"""Architecture boundary tests (SPEC-02 Dependency Rule; ADR-0003).

Machine-enforced: the domain layer never imports infrastructure,
presentation or framework modules, and the constitution-guarded
contexts have no import path to any LLM client.
"""

from __future__ import annotations

import ast
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2] / "backend"

FORBIDDEN_IN_DOMAIN = (
    "infrastructure",
    "api",
    "fastapi",
    "sqlalchemy",
    "alembic",
    "redis",
    "duckdb",
    "httpx",
    "requests",
)
LLM_FORBIDDEN = ("openai", "anthropic", "google", "llm_gateway", "langchain")
LLM_GUARDED_CONTEXTS = (
    "decision_kernel",
    "risk",
    "portfolio",
    "behavior",
    "dsl",
    "probability",
    "market",
    "backtest",
)


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text())
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module.split(".")[0])
    return found


def test_domain_layer_is_framework_free() -> None:
    violations: list[str] = []
    for path in BACKEND.glob("*/domain/**/*.py"):
        bad = _imports(path) & set(FORBIDDEN_IN_DOMAIN)
        if bad:
            violations.append(f"{path.relative_to(BACKEND)}: {sorted(bad)}")
    assert not violations, "domain layer must not import frameworks:\n" + "\n".join(violations)


def test_constitution_contexts_have_no_llm_import_path() -> None:
    violations: list[str] = []
    for context in LLM_GUARDED_CONTEXTS:
        for path in (BACKEND / context).rglob("*.py"):
            bad = _imports(path) & set(LLM_FORBIDDEN)
            if bad:
                violations.append(f"{path.relative_to(BACKEND)}: {sorted(bad)}")
    assert not violations, "ADR-0003 violated:\n" + "\n".join(violations)


def test_llm_gateway_never_reaches_decision_contexts() -> None:
    """ADR-0003: the gateway can never call into the Decision Kernel or
    any other guarded context — research flows one way, via reviewed
    artifacts, never by the gateway driving decisions."""
    violations: list[str] = []
    for path in (BACKEND / "llm_gateway").rglob("*.py"):
        bad = _imports(path) & set(LLM_GUARDED_CONTEXTS)
        if bad:
            violations.append(f"{path.relative_to(BACKEND)}: {sorted(bad)}")
    assert not violations, "llm_gateway imports guarded contexts:\n" + "\n".join(violations)


def test_no_sql_in_domain_or_application() -> None:
    """SPEC-06 §4: no SQL in services; the api composition root may wire
    the session factory type, but domain and application layers may not
    touch SQLAlchemy at all."""
    violations: list[str] = []
    for layer in ("domain", "application"):
        for path in BACKEND.glob(f"*/{layer}/**/*.py"):
            if "sqlalchemy" in _imports(path):
                violations.append(str(path.relative_to(BACKEND)))
    assert not violations, "SQL in domain/application:\n" + "\n".join(violations)


def test_application_layer_does_not_import_infrastructure() -> None:
    violations: list[str] = []
    for path in BACKEND.glob("*/application/**/*.py"):
        if "infrastructure" in _imports(path):
            violations.append(str(path.relative_to(BACKEND)))
    assert not violations, "application imports infrastructure:\n" + "\n".join(violations)
