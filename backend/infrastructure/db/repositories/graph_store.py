"""SQL implementation of the GraphStore port (ADR-0007).

Edges carry (created_version, removed_version] ranges: mutations append
rows or close ranges, never delete — any historical version of the graph
is reconstructable (RFC-0019 §8).
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from infrastructure.db.engine import session_scope
from infrastructure.db.models import KgEdgeRow, KgNodeRow
from knowledge.domain.graph import Edge, GraphError, GraphSnapshot, Node, NodeType, RelationType
from knowledge.domain.repository import GraphStore
from shared_kernel.exceptions import NotFoundError


class SqlGraphStore(GraphStore):
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._sessions = session_factory

    def _current_version(self, session: Session) -> int:
        newest = session.scalar(select(func.max(KgEdgeRow.created_version)))
        closed = session.scalar(select(func.max(KgEdgeRow.removed_version)))
        return max(int(newest or 0), int(closed or 0))

    def add_node(self, node: Node) -> None:
        with session_scope(self._sessions) as session:
            row = session.get(KgNodeRow, node.node_id)
            if row is None:
                session.add(
                    KgNodeRow(
                        node_id=node.node_id,
                        type=node.type.value,
                        name=node.name,
                        attributes=dict(node.attributes),
                        created_at=datetime.now(timezone.utc),
                    )
                )
                return
            if row.type != node.type.value:
                raise GraphError(
                    f"node {node.node_id} already exists with type {row.type}; "
                    "changing a node's type is forbidden"
                )
            row.name = node.name
            row.attributes = dict(node.attributes)

    def add_edge(self, edge: Edge) -> int:
        with session_scope(self._sessions) as session:
            for node_id in (edge.source_id, edge.target_id):
                if session.get(KgNodeRow, node_id) is None:
                    raise NotFoundError(f"unknown node: {node_id}")
            duplicate = session.scalar(
                select(KgEdgeRow).where(
                    KgEdgeRow.source_id == edge.source_id,
                    KgEdgeRow.target_id == edge.target_id,
                    KgEdgeRow.relation == edge.relation.value,
                    KgEdgeRow.removed_version.is_(None),
                )
            )
            if duplicate is not None:
                raise GraphError(
                    f"edge already active: {edge.source_id} "
                    f"-{edge.relation.value}-> {edge.target_id}"
                )
            version = self._current_version(session) + 1
            session.add(
                KgEdgeRow(
                    source_id=edge.source_id,
                    target_id=edge.target_id,
                    relation=edge.relation.value,
                    provenance=edge.provenance,
                    created_version=version,
                    removed_version=None,
                )
            )
            return version

    def remove_edge(self, edge: Edge) -> int:
        with session_scope(self._sessions) as session:
            row = session.scalar(
                select(KgEdgeRow).where(
                    KgEdgeRow.source_id == edge.source_id,
                    KgEdgeRow.target_id == edge.target_id,
                    KgEdgeRow.relation == edge.relation.value,
                    KgEdgeRow.removed_version.is_(None),
                )
            )
            if row is None:
                raise NotFoundError(
                    f"no active edge: {edge.source_id} -{edge.relation.value}-> {edge.target_id}"
                )
            version = self._current_version(session) + 1
            row.removed_version = version
            return version

    def snapshot(self, *, version: int | None = None) -> GraphSnapshot:
        with session_scope(self._sessions) as session:
            at = version if version is not None else self._current_version(session)
            node_rows = session.scalars(select(KgNodeRow)).all()
            nodes = {
                r.node_id: Node(
                    node_id=r.node_id,
                    type=NodeType(r.type),
                    name=r.name,
                    attributes={str(k): str(v) for k, v in r.attributes.items()},
                )
                for r in node_rows
            }
            edge_rows = session.scalars(
                select(KgEdgeRow)
                .where(KgEdgeRow.created_version <= at)
                .where((KgEdgeRow.removed_version.is_(None)) | (KgEdgeRow.removed_version > at))
                .order_by(KgEdgeRow.created_version)
            ).all()
            edges = tuple(
                Edge(
                    source_id=r.source_id,
                    relation=RelationType(r.relation),
                    target_id=r.target_id,
                    provenance=r.provenance,
                )
                for r in edge_rows
            )
            return GraphSnapshot(version=at, nodes=nodes, edges=edges)
