"use client";

import { useState } from "react";
import { CheckCircle2, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { useReviewDecision } from "@/hooks/queries";
import { useAuthStore } from "@/stores/auth-store";
import type { DecisionResponse } from "@/types/api";

/**
 * Human review workflow (SPEC-00: human approval is mandatory). Only
 * ANALYST/ADMIN may approve or reject, and only while the decision is
 * DRAFT or UNDER_REVIEW. RBAC is enforced server-side; the UI mirrors it.
 */
export function ReviewPanel({ decision }: { decision: DecisionResponse }) {
  const canReview = useAuthStore((s) => s.hasRole("ANALYST", "ADMIN"));
  const review = useReviewDecision(decision.id);
  const [note, setNote] = useState("");

  const reviewable = decision.status === "DRAFT" || decision.status === "UNDER_REVIEW";

  if (!reviewable) {
    return (
      <p className="text-sm text-muted-foreground">
        This decision is {decision.status.toLowerCase().replace("_", " ")} and is no longer open for
        review.
      </p>
    );
  }

  if (!canReview) {
    return (
      <p className="text-sm text-muted-foreground">
        You have read-only access. An analyst must approve or reject this decision.
      </p>
    );
  }

  return (
    <div className="space-y-3">
      <label htmlFor="review-note" className="text-sm font-medium">
        Reviewer note
      </label>
      <textarea
        id="review-note"
        rows={3}
        value={note}
        onChange={(e) => setNote(e.target.value)}
        placeholder="Record your rationale — this is written to the immutable audit trail."
        className="w-full rounded-md border bg-background p-2 text-sm focus-visible:ring-2 focus-visible:ring-ring"
      />
      {review.isError ? (
        <p role="alert" className="text-sm text-loss">
          Review failed. Please retry.
        </p>
      ) : null}
      <div className="flex gap-2">
        <Button
          onClick={() => review.mutate({ outcome: "APPROVED", note })}
          disabled={review.isPending}
        >
          {review.isPending ? <Spinner /> : <CheckCircle2 className="h-4 w-4" />}
          Approve
        </Button>
        <Button
          variant="destructive"
          onClick={() => review.mutate({ outcome: "REJECTED", note })}
          disabled={review.isPending}
        >
          <XCircle className="h-4 w-4" />
          Reject
        </Button>
      </div>
    </div>
  );
}
