/**
 * Pure dashboard derivations (Phase 6, WS2). These turn the decision list
 * the app already fetches into the summaries the widgets render — no new
 * endpoints, no business logic (counting and bucketing only). Kept pure so
 * they are unit-testable.
 */
import type { DecisionResponse, DecisionStatus, EvidenceOut, RiskLevel } from "@/types/api";

export const DECISION_STATUSES: DecisionStatus[] = [
  "DRAFT",
  "UNDER_REVIEW",
  "APPROVED",
  "REJECTED",
  "ARCHIVED",
];

export const RISK_LEVELS: RiskLevel[] = ["VERY_LOW", "LOW", "MODERATE", "HIGH", "CRITICAL"];

export function statusCounts(decisions: DecisionResponse[]): Record<DecisionStatus, number> {
  const out = Object.fromEntries(DECISION_STATUSES.map((s) => [s, 0])) as Record<
    DecisionStatus,
    number
  >;
  for (const d of decisions) out[d.status] = (out[d.status] ?? 0) + 1;
  return out;
}

export function riskLevelCounts(decisions: DecisionResponse[]): Record<RiskLevel, number> {
  const out = Object.fromEntries(RISK_LEVELS.map((r) => [r, 0])) as Record<RiskLevel, number>;
  for (const d of decisions) {
    const level = d.risk_assessment?.level;
    if (level) out[level] = (out[level] ?? 0) + 1;
  }
  return out;
}

export interface Bin {
  label: string;
  count: number;
}

/** Histogram of decision probabilities (0..1) into `bins` equal buckets. */
export function probabilityHistogram(decisions: DecisionResponse[], bins = 5): Bin[] {
  const counts = new Array(bins).fill(0) as number[];
  for (const d of decisions) {
    const p = Number(d.probability);
    if (!Number.isFinite(p)) continue;
    const idx = Math.min(bins - 1, Math.max(0, Math.floor(p * bins)));
    counts[idx] += 1;
  }
  return counts.map((count, i) => {
    const lo = Math.round((i / bins) * 100);
    const hi = Math.round(((i + 1) / bins) * 100);
    return { label: `${lo}–${hi}%`, count };
  });
}

export interface EvidenceRef {
  evidence: EvidenceOut;
  decisionId: string;
  hypothesis: string;
}

/** Most recent evidence items across all decisions, newest first. */
export function latestEvidence(decisions: DecisionResponse[], limit = 5): EvidenceRef[] {
  const refs: EvidenceRef[] = [];
  for (const d of decisions) {
    for (const e of d.evidence) {
      refs.push({ evidence: e, decisionId: d.id, hypothesis: d.hypothesis });
    }
  }
  refs.sort((a, b) => +new Date(b.evidence.timestamp) - +new Date(a.evidence.timestamp));
  return refs.slice(0, limit);
}

export interface Activity {
  id: string;
  label: string;
  detail: string;
  at: string;
  href: string;
}

/** Recent decision reviews (approve/reject/lifecycle) as an activity feed. */
export function reviewActivities(decisions: DecisionResponse[], limit = 8): Activity[] {
  const acts: Activity[] = [];
  for (const d of decisions) {
    for (const r of d.review_history) {
      acts.push({
        id: `${d.id}-${r.at}`,
        label: `Decision ${r.outcome.toLowerCase()}`,
        detail: d.hypothesis,
        at: r.at,
        href: `/decisions/${d.id}`,
      });
    }
  }
  acts.sort((a, b) => +new Date(b.at) - +new Date(a.at));
  return acts.slice(0, limit);
}
