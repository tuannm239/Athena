import { describe, expect, it } from "vitest";
import {
  latestEvidence,
  probabilityHistogram,
  reviewActivities,
  riskLevelCounts,
  statusCounts,
} from "@/lib/dashboard";
import type { DecisionResponse } from "@/types/api";

function decision(over: Partial<DecisionResponse>): DecisionResponse {
  return {
    id: "d",
    hypothesis: "h",
    probability: "0.5",
    confidence: "0.5",
    status: "DRAFT",
    decision_type: null,
    expected_return: null,
    expected_drawdown: null,
    expected_utility: null,
    position_size: null,
    portfolio_impact: null,
    assumptions: [],
    invalidation_conditions: [],
    explanation: null,
    evidence: [],
    risk_assessment: null,
    review_history: [],
    created_at: "2026-01-01T00:00:00Z",
    ...over,
  };
}

describe("dashboard derivations", () => {
  it("counts decisions by status with all buckets present", () => {
    const c = statusCounts([
      decision({ status: "APPROVED" }),
      decision({ status: "APPROVED" }),
      decision({ status: "UNDER_REVIEW" }),
    ]);
    expect(c.APPROVED).toBe(2);
    expect(c.UNDER_REVIEW).toBe(1);
    expect(c.DRAFT).toBe(0);
  });

  it("buckets probabilities into a histogram", () => {
    const bins = probabilityHistogram(
      [decision({ probability: "0.05" }), decision({ probability: "0.95" }), decision({ probability: "1" })],
      5,
    );
    expect(bins).toHaveLength(5);
    expect(bins[0].count).toBe(1); // 0-20%
    expect(bins[4].count).toBe(2); // 80-100% incl. 1.0 clamped
  });

  it("counts risk levels only when assessed", () => {
    const c = riskLevelCounts([
      decision({ risk_assessment: { level: "HIGH" } as DecisionResponse["risk_assessment"] }),
      decision({ risk_assessment: null }),
    ]);
    expect(c.HIGH).toBe(1);
    expect(c.LOW).toBe(0);
  });

  it("collects latest evidence newest-first", () => {
    const d = decision({
      id: "x",
      evidence: [
        { id: "e1", timestamp: "2026-01-01T00:00:00Z" } as DecisionResponse["evidence"][number],
        { id: "e2", timestamp: "2026-02-01T00:00:00Z" } as DecisionResponse["evidence"][number],
      ],
    });
    const refs = latestEvidence([d], 5);
    expect(refs.map((r) => r.evidence.id)).toEqual(["e2", "e1"]);
  });

  it("builds a review activity feed newest-first", () => {
    const d = decision({
      review_history: [
        { outcome: "APPROVED", at: "2026-01-01T00:00:00Z", note: "" },
        { outcome: "REJECTED", at: "2026-03-01T00:00:00Z", note: "" },
      ],
    });
    const acts = reviewActivities([d], 5);
    expect(acts[0].label).toContain("rejected");
  });
});
