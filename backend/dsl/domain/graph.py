"""Decision Graph (RFC-0020 §4; RFC-0017 §Decision Graph).

A directed acyclic graph: each rule is a node; dependencies are edges;
cycles are compiler errors (DSL009). Execution order is deterministic:
priority descending, then rule id ascending.
"""

from __future__ import annotations

from dataclasses import dataclass

from dsl.domain.errors import CircularDependencyError
from dsl.domain.ir import RuleIR


@dataclass(frozen=True, slots=True)
class DecisionGraph:
    nodes: tuple[RuleIR, ...]  # in execution order
    edges: tuple[tuple[str, str], ...]  # (from_rule, to_rule) dependency edges

    @property
    def execution_order(self) -> tuple[str, ...]:
        return tuple(node.rule_id for node in self.nodes)


def build_graph(rules: tuple[RuleIR, ...]) -> DecisionGraph:
    """Order nodes deterministically and verify acyclicity (DSL009)."""
    ordered = tuple(sorted(rules, key=lambda r: (-r.priority, r.rule_id)))
    edges: list[tuple[str, str]] = []
    for rule in ordered:
        for dependency in rule.dependencies:
            edges.append((dependency, rule.rule_id))

    # Kahn's algorithm over dependency edges (guards future dependency syntax).
    ids = {rule.rule_id for rule in ordered}
    incoming: dict[str, set[str]] = {rule_id: set() for rule_id in ids}
    for source, target in edges:
        if source in incoming and target in incoming:
            incoming[target].add(source)
    ready = sorted(rule_id for rule_id, deps in incoming.items() if not deps)
    visited: list[str] = []
    while ready:
        current = ready.pop(0)
        visited.append(current)
        for rule_id, deps in sorted(incoming.items()):
            if current in deps:
                deps.remove(current)
                if not deps and rule_id not in visited and rule_id not in ready:
                    ready.append(rule_id)
        ready.sort()
    if len(visited) != len(ids):
        cyclic = sorted(ids - set(visited))
        first = ordered[0].location
        raise CircularDependencyError(
            f"circular dependency among rules: {cyclic}",
            line=first.line,
            column=first.column,
        )
    return DecisionGraph(nodes=ordered, edges=tuple(edges))
