/**
 * Reusable column definitions for exports/reports (Phase 6, WS6/WS3).
 * Presentation mappings only — they read fields the API already returns.
 */
import type { Column } from "@/lib/export";
import type { DecisionResponse, EvidenceOut, PositionOut } from "@/types/api";
import { pct } from "@/lib/utils";

export const decisionColumns: Column<DecisionResponse>[] = [
  { header: "ID", accessor: (d) => d.id },
  { header: "Hypothesis", accessor: (d) => d.hypothesis },
  { header: "Status", accessor: (d) => d.status },
  { header: "Type", accessor: (d) => d.decision_type ?? "" },
  { header: "Probability", accessor: (d) => pct(d.probability) },
  { header: "Confidence", accessor: (d) => pct(d.confidence) },
  { header: "Expected utility", accessor: (d) => d.expected_utility ?? "" },
  { header: "Risk level", accessor: (d) => d.risk_assessment?.level ?? "" },
  { header: "Evidence #", accessor: (d) => d.evidence.length },
  { header: "Created", accessor: (d) => d.created_at },
];

export const evidenceColumns: Column<EvidenceOut>[] = [
  { header: "Category", accessor: (e) => e.category },
  { header: "Direction", accessor: (e) => e.direction },
  { header: "Source", accessor: (e) => e.source },
  { header: "Reliability", accessor: (e) => pct(e.reliability, 0) },
  { header: "Explanation", accessor: (e) => e.explanation },
  { header: "Timestamp", accessor: (e) => e.timestamp },
];

export const positionColumns: Column<PositionOut>[] = [
  { header: "Ticker", accessor: (p) => p.ticker },
  { header: "Quantity", accessor: (p) => p.quantity },
  { header: "Avg cost", accessor: (p) => p.average_cost },
  { header: "Market value", accessor: (p) => p.market_value },
  { header: "Unrealized P&L", accessor: (p) => p.unrealized_pnl },
  { header: "Currency", accessor: (p) => p.currency },
];
