"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { BookOpen, Building2, Factory, Globe2, Landmark, Layers } from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { EvidenceCard } from "@/components/ui/evidence-card";
import { NotesPanel } from "@/components/notes-panel";
import { useDecisions } from "@/hooks/queries";
import { formatDate } from "@/lib/utils";
import type { EvidenceOut } from "@/types/api";

type Axis = "Company" | "Industry" | "Sector" | "Macro" | "Regulations";
const AXES: { key: Axis; icon: typeof Building2 }[] = [
  { key: "Company", icon: Building2 },
  { key: "Industry", icon: Factory },
  { key: "Sector", icon: Layers },
  { key: "Macro", icon: Globe2 },
  { key: "Regulations", icon: Landmark },
];

/** Classify an evidence item into a research axis from its category/source. */
function classify(e: EvidenceOut): Axis {
  const s = `${e.category} ${e.source}`.toLowerCase();
  if (/regulat|policy|legal|circular|decree|ssc/.test(s)) return "Regulations";
  if (/macro|econom|rate|inflation|gdp|fx|currency|monetary/.test(s)) return "Macro";
  if (/sector/.test(s)) return "Sector";
  if (/industr/.test(s)) return "Industry";
  return "Company";
}

interface Ref {
  evidence: EvidenceOut;
  decisionId: string;
  hypothesis: string;
}

export default function ResearchPage() {
  const decisions = useDecisions({ limit: 100 });
  const [axis, setAxis] = useState<Axis>("Company");

  const byAxis = useMemo(() => {
    const map: Record<Axis, Ref[]> = {
      Company: [],
      Industry: [],
      Sector: [],
      Macro: [],
      Regulations: [],
    };
    for (const d of decisions.data?.items ?? []) {
      for (const e of d.evidence) {
        map[classify(e)].push({ evidence: e, decisionId: d.id, hypothesis: d.hypothesis });
      }
    }
    for (const key of Object.keys(map) as Axis[]) {
      map[key].sort((a, b) => +new Date(b.evidence.timestamp) - +new Date(a.evidence.timestamp));
    }
    return map;
  }, [decisions.data]);

  const refs = byAxis[axis];

  return (
    <>
      <PageHeader
        title="Research"
        description="Upload reports, keep notes, and browse the evidence corpus — organized by company, industry, sector, macro and regulations for the Vietnamese market. Every note carries an audit trail and human-review flag."
      />

      <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
        Research notes &amp; documents
      </h2>
      <div className="mb-6">
        <NotesPanel />
      </div>

      <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
        Evidence corpus
      </h2>
      <div className="mb-4 flex flex-wrap gap-1" role="tablist" aria-label="Research area">
        {AXES.map(({ key, icon: Icon }) => (
          <Button
            key={key}
            size="sm"
            variant={axis === key ? "default" : "ghost"}
            role="tab"
            aria-selected={axis === key}
            onClick={() => setAxis(key)}
          >
            <Icon className="h-3.5 w-3.5" /> {key}
            <Badge variant="muted" className="ml-1">
              {byAxis[key].length}
            </Badge>
          </Button>
        ))}
      </div>

      {decisions.isLoading ? (
        <Skeleton className="h-64 w-full" />
      ) : refs.length === 0 ? (
        <EmptyState
          icon={BookOpen}
          title={`No ${axis.toLowerCase()} research yet`}
          description="Research appears here as evidence is attached to decisions. Every note links back to its decision history."
        />
      ) : (
        <div className="space-y-3">
          {refs.map((r) => (
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
