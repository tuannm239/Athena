"""Integration tests — versioned SQL GraphStore (RFC-0019 §8; ADR-0007)."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from infrastructure.db.base import Base
from infrastructure.db.repositories.graph_store import SqlGraphStore
from knowledge.application.use_cases import KnowledgeGraphUseCases
from knowledge.domain.graph import Edge, GraphError, Node, NodeType, RelationType


@pytest.fixture()
def graph() -> KnowledgeGraphUseCases:
    engine = create_engine(
        "sqlite+pysqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    store = SqlGraphStore(sessionmaker(bind=engine, expire_on_commit=False))
    uc = KnowledgeGraphUseCases(store=store)
    uc.add_node(Node("company.abc", NodeType.COMPANY, "Company ABC"))
    uc.add_node(Node("company.xyz", NodeType.COMPANY, "Company XYZ"))
    uc.add_node(Node("industry.steel", NodeType.INDUSTRY, "Steel Industry"))
    return uc


class TestVersionedMutations:
    def test_history_remains_queryable(self, graph: KnowledgeGraphUseCases) -> None:
        v1 = graph.connect(
            Edge("company.abc", RelationType.BELONGS_TO, "industry.steel", "listing")
        )
        v2 = graph.connect(
            Edge("company.abc", RelationType.SUPPLIES, "company.xyz", "supply-chain")
        )
        v3 = graph.disconnect(
            Edge("company.abc", RelationType.SUPPLIES, "company.xyz", "supply-chain")
        )
        assert (v1, v2, v3) == (1, 2, 3)

        assert len(graph.snapshot(version=v2).edges) == 2
        assert len(graph.snapshot(version=v3).edges) == 1
        assert len(graph.snapshot(version=v1).edges) == 1
        assert graph.neighbors("company.xyz", version=v2) == ("company.abc",)
        assert graph.neighbors("company.xyz", version=v3) == ()

    def test_duplicate_active_edge_rejected(self, graph: KnowledgeGraphUseCases) -> None:
        edge = Edge("company.abc", RelationType.BELONGS_TO, "industry.steel", "listing")
        graph.connect(edge)
        with pytest.raises(GraphError):
            graph.connect(edge)

    def test_cycles_require_explicit_permission(self, graph: KnowledgeGraphUseCases) -> None:
        graph.connect(Edge("company.abc", RelationType.SUPPLIES, "company.xyz", "s"))
        back = Edge("company.xyz", RelationType.SUPPLIES, "company.abc", "s")
        with pytest.raises(GraphError):
            graph.connect(back)
        version = graph.connect(back, allow_cycle=True)
        assert version == 2

    def test_node_type_change_forbidden(self, graph: KnowledgeGraphUseCases) -> None:
        with pytest.raises(GraphError):
            graph.add_node(Node("company.abc", NodeType.SECTOR, "ABC"))

    def test_reasoning_over_store(self, graph: KnowledgeGraphUseCases) -> None:
        graph.connect(Edge("company.abc", RelationType.BELONGS_TO, "industry.steel", "listing"))
        graph.connect(Edge("company.abc", RelationType.SUPPLIES, "company.xyz", "s"))
        assert graph.impacts("company.abc") == ("company.xyz", "industry.steel") or graph.impacts(
            "company.abc"
        ) == ("industry.steel", "company.xyz")
        assert graph.explain("company.abc", "industry.steel") == (
            "Company ABC -[BELONGS_TO]-> Steel Industry"
        )
