"""Unit tests — Knowledge Graph domain and traversal (RFC-0019)."""

from __future__ import annotations

import pytest

from knowledge.domain.graph import (
    Edge,
    GraphError,
    GraphSnapshot,
    Node,
    NodeType,
    RelationType,
)
from knowledge.domain.traversal import (
    explain_relationship,
    find_dependencies,
    find_impacts,
    find_neighbors,
    shortest_path,
    traverse,
)


def nodes() -> dict[str, Node]:
    entries = (
        Node("macro.rates", NodeType.MACRO_INDICATOR, "Interest Rate"),
        Node("sector.banking", NodeType.SECTOR, "Banking Sector"),
        Node("sector.realestate", NodeType.SECTOR, "Real Estate Sector"),
        Node("industry.steel", NodeType.INDUSTRY, "Steel Industry"),
        Node("commodity.iron", NodeType.COMMODITY, "Iron Ore"),
        Node("company.abc", NodeType.COMPANY, "Company ABC"),
        Node("company.xyz", NodeType.COMPANY, "Company XYZ"),
        Node("decision.12345", NodeType.DECISION, "Decision #12345"),
    )
    return {n.node_id: n for n in entries}


def edges() -> tuple[Edge, ...]:
    return (
        Edge("macro.rates", RelationType.INFLUENCES, "sector.banking", "curated"),
        Edge("macro.rates", RelationType.INFLUENCES, "sector.realestate", "curated"),
        Edge("commodity.iron", RelationType.IMPACTS, "industry.steel", "curated"),
        Edge("company.abc", RelationType.BELONGS_TO, "industry.steel", "listing"),
        Edge("industry.steel", RelationType.BELONGS_TO, "sector.realestate", "curated"),
        Edge("company.abc", RelationType.SUPPLIES, "company.xyz", "supply-chain db"),
        Edge("decision.12345", RelationType.REFERENCES, "company.abc", "decision kernel"),
    )


def snapshot() -> GraphSnapshot:
    return GraphSnapshot(version=1, nodes=nodes(), edges=edges())


class TestGraphRules:
    def test_edges_require_provenance(self) -> None:
        with pytest.raises(GraphError):
            Edge("a", RelationType.SUPPLIES, "b", "")

    def test_relation_catalogue_enforced(self) -> None:
        bad = Edge("company.abc", RelationType.INFLUENCES, "sector.banking", "curated")
        with pytest.raises(GraphError):
            GraphSnapshot(version=1, nodes=nodes(), edges=(bad,))

    def test_unknown_nodes_rejected(self) -> None:
        dangling = Edge("company.abc", RelationType.SUPPLIES, "company.missing", "x")
        with pytest.raises(GraphError):
            GraphSnapshot(version=1, nodes=nodes(), edges=(dangling,))

    def test_cycle_detection(self) -> None:
        snap = snapshot()
        assert snap.would_create_cycle("company.abc", "company.xyz") is False
        assert snap.would_create_cycle("company.xyz", "company.abc") is True


class TestTraversal:
    def test_neighbors_are_sorted_and_bidirectional(self) -> None:
        assert find_neighbors(snapshot(), "industry.steel") == (
            "commodity.iron",
            "company.abc",
            "sector.realestate",
        )

    def test_impacts_downstream(self) -> None:
        assert find_impacts(snapshot(), "commodity.iron") == (
            "industry.steel",
            "sector.realestate",
        )

    def test_dependencies_upstream(self) -> None:
        deps = find_dependencies(snapshot(), "sector.realestate")
        assert set(deps) == {
            "macro.rates",
            "industry.steel",
            "commodity.iron",
            "company.abc",
            "decision.12345",
        }

    def test_traverse_depth_limited(self) -> None:
        assert traverse(snapshot(), "commodity.iron", max_depth=1) == ("industry.steel",)

    def test_shortest_path_and_explanation(self) -> None:
        path = shortest_path(snapshot(), "decision.12345", "industry.steel")
        assert path is not None and len(path.edges) == 2
        text = explain_relationship(snapshot(), "decision.12345", "industry.steel")
        assert text == (
            "Decision #12345 -[REFERENCES]-> Company ABC -[BELONGS_TO]-> Steel Industry"
        )

    def test_unreachable_is_explicit(self) -> None:
        assert explain_relationship(snapshot(), "company.xyz", "macro.rates").startswith(
            "no directed relationship path"
        )

    def test_traversal_is_deterministic(self) -> None:
        runs = {find_impacts(snapshot(), "macro.rates") for _ in range(5)}
        assert len(runs) == 1
