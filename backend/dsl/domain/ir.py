"""Intermediate representation (RFC-0020 §5; RFC-0017 §IR).

The IR is immutable and carries rule id, priority, conditions, actions,
dependencies, tags, metadata and source location. Under the v2 grammar
rules declare no explicit dependencies; execution order is defined by
(priority descending, name ascending), which is acyclic by construction
— DSL009 remains guarded in the graph builder for future dependency
syntax.
"""

from __future__ import annotations

from dataclasses import dataclass

from dsl.domain.ast import ActionNode, ExpressionNode, RuleNode, SourceLocation, TagNode

DEFAULT_PRIORITY = 1


@dataclass(frozen=True, slots=True)
class RuleIR:
    rule_id: str
    version: str | None
    priority: int
    condition: ExpressionNode
    actions: tuple[ActionNode, ...]
    tags: tuple[str, ...]
    explain: str | None
    dependencies: tuple[str, ...]
    location: SourceLocation


def lower_rule(rule: RuleNode) -> RuleIR:
    """AST → IR; deterministic, no information loss."""
    return RuleIR(
        rule_id=rule.name,
        version=rule.metadata.version,
        priority=rule.metadata.priority or DEFAULT_PRIORITY,
        condition=rule.when,
        actions=rule.actions,
        tags=tuple(tag.value for tag in rule.tags),
        explain=rule.explain.text if rule.explain else None,
        dependencies=(),
        location=rule.location,
    )


def _tags_of(tags: tuple[TagNode, ...]) -> tuple[str, ...]:  # pragma: no cover - helper alias
    return tuple(t.value for t in tags)
