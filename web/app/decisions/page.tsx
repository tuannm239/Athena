"use client";

import Link from "next/link";
import { useState } from "react";
import { Target } from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { DecisionStatusBadge } from "@/components/ui/decision-status-badge";
import { useDecisions } from "@/hooks/queries";
import { formatDate, pct } from "@/lib/utils";
import type { DecisionStatus } from "@/types/api";

const FILTERS: (DecisionStatus | "ALL")[] = [
  "ALL",
  "DRAFT",
  "UNDER_REVIEW",
  "APPROVED",
  "REJECTED",
  "ARCHIVED",
];

export default function DecisionsPage() {
  const [status, setStatus] = useState<DecisionStatus | "ALL">("ALL");
  const [page, setPage] = useState(0);
  const limit = 20;
  const query = useDecisions({
    limit,
    offset: page * limit,
    status: status === "ALL" ? undefined : status,
  });

  return (
    <>
      <PageHeader
        title="Decision Center"
        description="Every hypothesis Athena has evaluated. Human approval is mandatory before any decision is acted on."
      />

      <div className="mb-4 flex flex-wrap gap-1" role="tablist" aria-label="Filter by status">
        {FILTERS.map((f) => (
          <Button
            key={f}
            size="sm"
            variant={status === f ? "default" : "ghost"}
            role="tab"
            aria-selected={status === f}
            onClick={() => {
              setStatus(f);
              setPage(0);
            }}
          >
            {f.replace("_", " ")}
          </Button>
        ))}
      </div>

      <Card>
        <CardContent className="p-0">
          {query.isLoading ? (
            <div className="space-y-2 p-4">
              {[0, 1, 2, 3, 4].map((i) => (
                <Skeleton key={i} className="h-14 w-full" />
              ))}
            </div>
          ) : query.data && query.data.items.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="border-b text-left text-xs uppercase text-muted-foreground">
                  <tr>
                    <th className="p-3 font-medium">Hypothesis</th>
                    <th className="p-3 font-medium">Probability</th>
                    <th className="p-3 font-medium">Confidence</th>
                    <th className="p-3 font-medium">Status</th>
                    <th className="p-3 font-medium">Created</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {query.data.items.map((d) => (
                    <tr key={d.id} className="hover:bg-accent/50">
                      <td className="max-w-md p-3">
                        <Link href={`/decisions/${d.id}`} className="font-medium hover:underline">
                          <span className="line-clamp-1">{d.hypothesis}</span>
                        </Link>
                      </td>
                      <td className="p-3 tabular-nums">{pct(d.probability)}</td>
                      <td className="p-3 tabular-nums text-muted-foreground">
                        {pct(d.confidence)}
                      </td>
                      <td className="p-3">
                        <DecisionStatusBadge status={d.status} />
                      </td>
                      <td className="p-3 text-muted-foreground">{formatDate(d.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState
              icon={Target}
              title="No decisions"
              description="No decisions match this filter yet."
              className="m-4"
            />
          )}
        </CardContent>
      </Card>

      {query.data && query.data.total > limit ? (
        <div className="mt-4 flex items-center justify-between text-sm">
          <span className="text-muted-foreground">
            {page * limit + 1}–{Math.min((page + 1) * limit, query.data.total)} of{" "}
            {query.data.total}
          </span>
          <div className="flex gap-2">
            <Button
              size="sm"
              variant="outline"
              disabled={page === 0}
              onClick={() => setPage((p) => Math.max(0, p - 1))}
            >
              Previous
            </Button>
            <Button
              size="sm"
              variant="outline"
              disabled={(page + 1) * limit >= query.data.total}
              onClick={() => setPage((p) => p + 1)}
            >
              Next
            </Button>
          </div>
        </div>
      ) : null}
    </>
  );
}
