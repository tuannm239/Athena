"""Decision Compiler (RFC-0020): DSL source → IR → Decision Graph.

Deterministic and pure — no I/O, no network, no database, no LLM
(RFC-0020 §2). Identical source produces an identical AST, IR and
Decision Graph (RFC-0017 acceptance criteria).
"""

from __future__ import annotations

from dataclasses import dataclass

from dsl.domain.graph import DecisionGraph, build_graph
from dsl.domain.ir import RuleIR, lower_rule
from dsl.domain.parser import parse
from dsl.domain.schema import DEFAULT_SCHEMA, PropertySpec
from dsl.domain.semantic import SemanticAnalyzer

COMPILER_VERSION = "athena-dslc/1.0.0"


@dataclass(frozen=True, slots=True)
class CompiledRuleset:
    """Immutable compilation artifact carried into the Decision Kernel."""

    graph: DecisionGraph
    rules: tuple[RuleIR, ...]
    compiler_version: str

    @property
    def rule_ids(self) -> tuple[str, ...]:
        return self.graph.execution_order


def compile_rules(
    source: str,
    *,
    schema: dict[str, dict[str, PropertySpec]] | None = None,
) -> CompiledRuleset:
    """Lexer → Parser → Semantic Analyzer → Rule Validator → IR → Graph."""
    program = SemanticAnalyzer(schema=schema or DEFAULT_SCHEMA).analyze(parse(source))
    rules = tuple(lower_rule(rule) for rule in program.rules)
    return CompiledRuleset(graph=build_graph(rules), rules=rules, compiler_version=COMPILER_VERSION)
