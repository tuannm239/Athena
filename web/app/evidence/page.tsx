"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { FileSearch } from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { EvidenceCard } from "@/components/ui/evidence-card";
import { ExportMenu } from "@/components/export-menu";
import { useDecisions } from "@/hooks/queries";
import { evidenceColumns } from "@/lib/report-columns";
import { formatDate } from "@/lib/utils";
import type { EvidenceDirection, EvidenceOut } from "@/types/api";

const FILTERS: (EvidenceDirection | "ALL")[] = ["ALL", "SUPPORTING", "CONTRADICTING", "NEUTRAL"];

interface Ref {
  evidence: EvidenceOut;
  decisionId: string;
  hypothesis: string;
}

export default function EvidenceCenterPage() {
  const decisions = useDecisions({ limit: 100 });
  const [dir, setDir] = useState<EvidenceDirection | "ALL">("ALL");

  const refs = useMemo<Ref[]>(() => {
    const out: Ref[] = [];
    for (const d of decisions.data?.items ?? []) {
      for (const e of d.evidence) {
        out.push({ evidence: e, decisionId: d.id, hypothesis: d.hypothesis });
      }
    }
    out.sort((a, b) => +new Date(b.evidence.timestamp) - +new Date(a.evidence.timestamp));
    return out;
  }, [decisions.data]);

  const filtered = dir === "ALL" ? refs : refs.filter((r) => r.evidence.direction === dir);

  return (
    <>
      <PageHeader
        title="Evidence Center"
        description="Every piece of evidence across all decisions — supporting, contradicting and neutral. Each links back to its decision."
        actions={
          <ExportMenu
            filename="athena-evidence"
            title="Athena — Evidence"
            columns={evidenceColumns}
            rows={filtered.map((r) => r.evidence)}
            pdf={{ orientation: "l" }}
          />
        }
      />

      <div className="mb-4 flex flex-wrap gap-1" role="tablist" aria-label="Filter by direction">
        {FILTERS.map((f) => (
          <Button
            key={f}
            size="sm"
            variant={dir === f ? "default" : "ghost"}
            role="tab"
            aria-selected={dir === f}
            onClick={() => setDir(f)}
          >
            {f}
            <Badge variant="muted" className="ml-1">
              {f === "ALL" ? refs.length : refs.filter((r) => r.evidence.direction === f).length}
            </Badge>
          </Button>
        ))}
      </div>

      {decisions.isLoading ? (
        <Skeleton className="h-64 w-full" />
      ) : filtered.length === 0 ? (
        <EmptyState
          icon={FileSearch}
          title="No evidence yet"
          description="Evidence attached to decisions appears here."
        />
      ) : (
        <div className="space-y-3">
          {filtered.map((r) => (
            <div key={r.evidence.id}>
              <EvidenceCard evidence={r.evidence} />
              <div className="mt-1 flex items-center justify-between px-1 text-xs text-muted-foreground">
                <Link href={`/decisions/${r.decisionId}`} className="text-primary hover:underline">
                  ↳ {r.hypothesis}
                </Link>
                <span>{formatDate(r.evidence.timestamp)}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </>
  );
}
