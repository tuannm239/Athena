"""Knowledge Graph public services (RFC-0019 §9).

FindNeighbors, FindImpacts, FindDependencies, ExplainRelationship,
Traverse — plus versioned mutations with cycle control (§5, §8).
"""

from __future__ import annotations

from dataclasses import dataclass

from knowledge.domain.graph import Edge, GraphError, GraphSnapshot, Node
from knowledge.domain.repository import GraphStore
from knowledge.domain.traversal import (
    explain_relationship,
    find_dependencies,
    find_impacts,
    find_neighbors,
    traverse,
)


@dataclass
class KnowledgeGraphUseCases:
    store: GraphStore

    def add_node(self, node: Node) -> None:
        self.store.add_node(node)

    def connect(self, edge: Edge, *, allow_cycle: bool = False) -> int:
        """Add a relationship; cycles require explicit permission (RFC-0019 §5)."""
        snapshot = self.store.snapshot()
        if not allow_cycle and snapshot.would_create_cycle(edge.source_id, edge.target_id):
            raise GraphError(
                f"edge {edge.source_id}->{edge.target_id} creates a cycle; "
                "pass allow_cycle=True to define it explicitly"
            )
        return self.store.add_edge(edge)

    def disconnect(self, edge: Edge) -> int:
        return self.store.remove_edge(edge)

    def snapshot(self, *, version: int | None = None) -> GraphSnapshot:
        return self.store.snapshot(version=version)

    # -- reasoning services (deterministic, read-only) ----------------------

    def neighbors(self, node_id: str, *, version: int | None = None) -> tuple[str, ...]:
        return find_neighbors(self.store.snapshot(version=version), node_id)

    def impacts(self, node_id: str, *, version: int | None = None) -> tuple[str, ...]:
        return find_impacts(self.store.snapshot(version=version), node_id)

    def dependencies(self, node_id: str, *, version: int | None = None) -> tuple[str, ...]:
        return find_dependencies(self.store.snapshot(version=version), node_id)

    def traverse(
        self, start: str, *, max_depth: int, version: int | None = None
    ) -> tuple[str, ...]:
        return traverse(self.store.snapshot(version=version), start, max_depth=max_depth)

    def explain(self, source: str, target: str, *, version: int | None = None) -> str:
        return explain_relationship(self.store.snapshot(version=version), source, target)
