import { ArrowDownRight, ArrowUpRight, Minus } from "lucide-react";
import { Badge } from "./badge";
import { pct } from "@/lib/utils";
import type { EvidenceOut } from "@/types/api";

const DIRECTION = {
  SUPPORTING: { icon: ArrowUpRight, variant: "gain" as const, label: "Supporting" },
  CONTRADICTING: { icon: ArrowDownRight, variant: "loss" as const, label: "Contradicting" },
  NEUTRAL: { icon: Minus, variant: "muted" as const, label: "Neutral" },
};

export function EvidenceCard({ evidence }: { evidence: EvidenceOut }) {
  const d = DIRECTION[evidence.direction];
  const Icon = d.icon;
  return (
    <div className="rounded-md border p-3">
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <Icon className={`h-4 w-4 ${evidence.direction === "SUPPORTING" ? "text-gain" : evidence.direction === "CONTRADICTING" ? "text-loss" : "text-muted-foreground"}`} aria-hidden />
          <span className="text-sm font-medium">{evidence.category}</span>
        </div>
        <Badge variant={d.variant}>{d.label}</Badge>
      </div>
      <p className="mt-2 text-sm text-foreground/90">{evidence.explanation}</p>
      <div className="mt-2 flex items-center justify-between text-xs text-muted-foreground">
        <span>Source: {evidence.source}</span>
        <span className="tabular-nums">Reliability {pct(evidence.reliability, 0)}</span>
      </div>
      {evidence.metadata?.source_type === "llm" ? (
        <div className="mt-1 text-[10px] uppercase tracking-wide text-warn">
          LLM-extracted · {evidence.metadata.model}
        </div>
      ) : null}
    </div>
  );
}
