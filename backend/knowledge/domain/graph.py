"""Knowledge Graph nodes, edges and snapshots (RFC-0019 §3–§5).

Graph rules encoded here:
- Relationships are directed and carry a semantic type.
- Every edge has provenance.
- Edge type-pairs must match the RFC-0019 §4 catalogue.
- Nodes have globally unique identifiers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Mapping

from shared_kernel.exceptions import DomainError


class GraphError(DomainError):
    """Violated graph rule (RFC-0019 §5)."""


class NodeType(StrEnum):
    COMPANY = "COMPANY"
    INDUSTRY = "INDUSTRY"
    SECTOR = "SECTOR"
    COUNTRY = "COUNTRY"
    CURRENCY = "CURRENCY"
    COMMODITY = "COMMODITY"
    MACRO_INDICATOR = "MACRO_INDICATOR"
    EVENT = "EVENT"
    DECISION = "DECISION"
    EVIDENCE = "EVIDENCE"  # §4 target; added by ADR-0007


class RelationType(StrEnum):
    BELONGS_TO = "BELONGS_TO"
    SUPPLIES = "SUPPLIES"
    COMPETES_WITH = "COMPETES_WITH"
    IMPACTS = "IMPACTS"
    INFLUENCES = "INFLUENCES"
    AFFECTS = "AFFECTS"
    REFERENCES = "REFERENCES"
    SUPPORTED_BY = "SUPPORTED_BY"
    CONTRADICTED_BY = "CONTRADICTED_BY"


# RFC-0019 §4 relationship catalogue: (source type, relation, target type).
ALLOWED_RELATIONS: frozenset[tuple[NodeType, RelationType, NodeType]] = frozenset(
    {
        (NodeType.COMPANY, RelationType.BELONGS_TO, NodeType.INDUSTRY),
        (NodeType.INDUSTRY, RelationType.BELONGS_TO, NodeType.SECTOR),
        (NodeType.COMPANY, RelationType.SUPPLIES, NodeType.COMPANY),
        (NodeType.COMPANY, RelationType.COMPETES_WITH, NodeType.COMPANY),
        (NodeType.COMMODITY, RelationType.IMPACTS, NodeType.INDUSTRY),
        (NodeType.MACRO_INDICATOR, RelationType.INFLUENCES, NodeType.SECTOR),
        (NodeType.EVENT, RelationType.AFFECTS, NodeType.COMPANY),
        (NodeType.DECISION, RelationType.REFERENCES, NodeType.COMPANY),
        (NodeType.DECISION, RelationType.SUPPORTED_BY, NodeType.EVIDENCE),
        (NodeType.DECISION, RelationType.CONTRADICTED_BY, NodeType.EVIDENCE),
    }
)


@dataclass(frozen=True, slots=True)
class Node:
    node_id: str
    type: NodeType
    name: str
    attributes: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.node_id:
            raise GraphError("node requires a globally unique id")
        if not self.name:
            raise GraphError("node requires a name")
        object.__setattr__(self, "attributes", MappingProxyType(dict(self.attributes)))


@dataclass(frozen=True, slots=True)
class Edge:
    source_id: str
    relation: RelationType
    target_id: str
    provenance: str

    def __post_init__(self) -> None:
        if not self.provenance:
            raise GraphError("every edge requires provenance (RFC-0019 §5)")
        if self.source_id == self.target_id:
            raise GraphError("self-referencing edges are not allowed")


@dataclass(frozen=True)
class GraphSnapshot:
    """Immutable view of the graph at one version; traversal input."""

    version: int
    nodes: Mapping[str, Node]
    edges: tuple[Edge, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "nodes", MappingProxyType(dict(self.nodes)))
        for edge in self.edges:
            self._check_edge(edge)

    def _check_edge(self, edge: Edge) -> None:
        source = self.nodes.get(edge.source_id)
        target = self.nodes.get(edge.target_id)
        if source is None or target is None:
            raise GraphError(f"edge references unknown node: {edge.source_id}->{edge.target_id}")
        if (source.type, edge.relation, target.type) not in ALLOWED_RELATIONS:
            raise GraphError(
                f"relation not in RFC-0019 catalogue: "
                f"{source.type} -{edge.relation}-> {target.type}"
            )

    def outgoing(self, node_id: str) -> tuple[Edge, ...]:
        return tuple(
            sorted(
                (e for e in self.edges if e.source_id == node_id),
                key=lambda e: (e.relation.value, e.target_id),
            )
        )

    def incoming(self, node_id: str) -> tuple[Edge, ...]:
        return tuple(
            sorted(
                (e for e in self.edges if e.target_id == node_id),
                key=lambda e: (e.relation.value, e.source_id),
            )
        )

    def would_create_cycle(self, source_id: str, target_id: str) -> bool:
        """True if an edge source→target closes a directed cycle."""
        stack, seen = [target_id], {target_id}
        while stack:
            current = stack.pop()
            if current == source_id:
                return True
            for edge in self.outgoing(current):
                if edge.target_id not in seen:
                    seen.add(edge.target_id)
                    stack.append(edge.target_id)
        return False
