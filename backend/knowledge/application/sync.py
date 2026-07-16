"""Knowledge Graph company/sector synchronization (Phase 2, Module 3).

Materializes provider sector classifications as the RFC-0019 §4 chain
COMPANY —BELONGS_TO→ INDUSTRY —BELONGS_TO→ SECTOR. Idempotent: nodes
upsert by id and edges are only added when no identical active edge
exists, so repeated syncs leave the graph version unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from knowledge.application.use_cases import KnowledgeGraphUseCases
from knowledge.domain.graph import Edge, Node, NodeType, RelationType
from providers.sdk.ports import SectorProvider


@dataclass
class KnowledgeSyncService:
    graph: KnowledgeGraphUseCases
    provider: SectorProvider
    provenance: str = "provider:sector"

    def sync_companies(self, tickers: Iterable[str]) -> tuple[str, ...]:
        """Sync classifications for the tickers; returns those found upstream."""
        existing = {
            (edge.source_id, edge.relation, edge.target_id) for edge in self.graph.snapshot().edges
        }
        synced: list[str] = []
        for ticker in sorted(set(tickers)):
            mapping = self.provider.classification(ticker)
            if mapping is None:
                continue
            company_id = f"company.{ticker}"
            industry_id = f"industry.{mapping.industry}"
            sector_id = f"sector.{mapping.sector}"

            attributes = {"exchange": mapping.exchange} if mapping.exchange else {}
            self.graph.add_node(Node(company_id, NodeType.COMPANY, ticker, attributes))
            self.graph.add_node(Node(industry_id, NodeType.INDUSTRY, mapping.industry))
            self.graph.add_node(Node(sector_id, NodeType.SECTOR, mapping.sector))

            for source_id, relation, target_id in (
                (company_id, RelationType.BELONGS_TO, industry_id),
                (industry_id, RelationType.BELONGS_TO, sector_id),
            ):
                if (source_id, relation, target_id) not in existing:
                    self.graph.connect(Edge(source_id, relation, target_id, self.provenance))
                    existing.add((source_id, relation, target_id))
            synced.append(ticker)
        return tuple(synced)
