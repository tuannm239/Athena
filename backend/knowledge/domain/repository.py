"""GraphStore port (ADR-0007): versioned, auditable, reproducible (RFC-0019 §8)."""

from __future__ import annotations

from abc import ABC, abstractmethod

from knowledge.domain.graph import Edge, GraphSnapshot, Node


class GraphStore(ABC):
    @abstractmethod
    def add_node(self, node: Node) -> None:
        """Idempotent on node_id; changing an existing node's type is forbidden."""

    @abstractmethod
    def add_edge(self, edge: Edge) -> int:
        """Append an edge; returns the new graph version."""

    @abstractmethod
    def remove_edge(self, edge: Edge) -> int:
        """Close an edge's version range; history stays queryable."""

    @abstractmethod
    def snapshot(self, *, version: int | None = None) -> GraphSnapshot:
        """Graph at a version (latest when None)."""
