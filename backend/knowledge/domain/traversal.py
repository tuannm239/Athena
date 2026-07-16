"""Deterministic graph reasoning (RFC-0019 §6, §9).

FindNeighbors, FindImpacts (downstream), FindDependencies (upstream),
Traverse, shortest path and ExplainRelationship. All functions are pure
over a GraphSnapshot and return deterministically ordered results.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from knowledge.domain.graph import Edge, GraphSnapshot


@dataclass(frozen=True, slots=True)
class RelationshipPath:
    """An explainable path: alternating node ids and semantic relations."""

    edges: tuple[Edge, ...]

    def render(self, snapshot: GraphSnapshot) -> str:
        """Human-readable explanation of the path (RFC-0019 §9)."""
        if not self.edges:
            return ""
        parts = [snapshot.nodes[self.edges[0].source_id].name]
        for edge in self.edges:
            parts.append(f"-[{edge.relation.value}]->")
            parts.append(snapshot.nodes[edge.target_id].name)
        return " ".join(parts)


def find_neighbors(snapshot: GraphSnapshot, node_id: str) -> tuple[str, ...]:
    """Directly connected node ids, either direction, deterministic order."""
    neighbors = {e.target_id for e in snapshot.outgoing(node_id)}
    neighbors |= {e.source_id for e in snapshot.incoming(node_id)}
    return tuple(sorted(neighbors))


def _reachable(snapshot: GraphSnapshot, start: str, *, downstream: bool) -> tuple[str, ...]:
    seen: set[str] = set()
    queue = deque([start])
    order: list[str] = []
    while queue:
        current = queue.popleft()
        edges = snapshot.outgoing(current) if downstream else snapshot.incoming(current)
        for edge in edges:
            nxt = edge.target_id if downstream else edge.source_id
            if nxt not in seen and nxt != start:
                seen.add(nxt)
                order.append(nxt)
                queue.append(nxt)
    return tuple(order)


def find_impacts(snapshot: GraphSnapshot, node_id: str) -> tuple[str, ...]:
    """Downstream impact: everything reachable along edge direction."""
    return _reachable(snapshot, node_id, downstream=True)


def find_dependencies(snapshot: GraphSnapshot, node_id: str) -> tuple[str, ...]:
    """Upstream dependencies: everything that can reach this node."""
    return _reachable(snapshot, node_id, downstream=False)


def traverse(snapshot: GraphSnapshot, start: str, *, max_depth: int) -> tuple[str, ...]:
    """Breadth-first traversal along edge direction up to max_depth."""
    if max_depth < 0:
        raise ValueError("max_depth must be non-negative")
    seen = {start}
    frontier = [start]
    order: list[str] = []
    for _ in range(max_depth):
        next_frontier: list[str] = []
        for node in frontier:
            for edge in snapshot.outgoing(node):
                if edge.target_id not in seen:
                    seen.add(edge.target_id)
                    order.append(edge.target_id)
                    next_frontier.append(edge.target_id)
        frontier = next_frontier
    return tuple(order)


def shortest_path(snapshot: GraphSnapshot, source: str, target: str) -> RelationshipPath | None:
    """Deterministic BFS shortest path along edge direction; None if unreachable."""
    if source == target:
        return RelationshipPath(edges=())
    parents: dict[str, Edge] = {}
    seen = {source}
    queue = deque([source])
    while queue:
        current = queue.popleft()
        for edge in snapshot.outgoing(current):
            if edge.target_id in seen:
                continue
            parents[edge.target_id] = edge
            if edge.target_id == target:
                path: list[Edge] = []
                node = target
                while node != source:
                    step = parents[node]
                    path.append(step)
                    node = step.source_id
                return RelationshipPath(edges=tuple(reversed(path)))
            seen.add(edge.target_id)
            queue.append(edge.target_id)
    return None


def explain_relationship(snapshot: GraphSnapshot, source: str, target: str) -> str:
    """ExplainRelationship(): rendered shortest path, or an explicit negative."""
    path = shortest_path(snapshot, source, target)
    if path is None:
        return f"no directed relationship path from {source} to {target}"
    if not path.edges:
        return snapshot.nodes[source].name
    return path.render(snapshot)
