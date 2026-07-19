"use client";

import { useMemo, useState } from "react";
import { Brain, Plus, Trash2 } from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Stat } from "@/components/ui/stat";
import { Gauge } from "@/components/ui/gauge";
import { LineChart } from "@/components/ui/line-chart";
import { bayesianUpdate, type EvidenceLikelihood } from "@/lib/analysis";

const DEFAULT_EVIDENCE: EvidenceLikelihood[] = [
  { label: "Earnings beat", ifTrue: 0.8, ifFalse: 0.3 },
  { label: "Sector tailwind", ifTrue: 0.6, ifFalse: 0.4 },
];

export default function ProbabilityPage() {
  const [prior, setPrior] = useState(0.5);
  const [evidence, setEvidence] = useState<EvidenceLikelihood[]>(DEFAULT_EVIDENCE);

  const steps = useMemo(() => bayesianUpdate(prior, evidence), [prior, evidence]);
  const posterior = steps.length ? steps[steps.length - 1].posterior : prior;
  const path = [prior, ...steps.map((s) => s.posterior)];

  function update(i: number, patch: Partial<EvidenceLikelihood>) {
    setEvidence((e) => e.map((row, idx) => (idx === i ? { ...row, ...patch } : row)));
  }

  return (
    <>
      <PageHeader
        title="Probability Studio"
        description="Update a prior with evidence using Bayesian likelihood ratios (RFC-0026). Computed live — a reasoning aid; the human decides."
      />

      <div className="grid gap-4 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>Prior</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <input
              type="range"
              min={0}
              max={1}
              step={0.01}
              value={prior}
              onChange={(e) => setPrior(Number(e.target.value))}
              className="w-full"
              aria-label="Prior probability"
            />
            <Stat label="Prior P(H)" value={`${(prior * 100).toFixed(0)}%`} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Posterior</CardTitle>
          </CardHeader>
          <CardContent className="flex justify-center">
            <Gauge value={posterior} label="posterior" tone="primary" />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Update Path</CardTitle>
          </CardHeader>
          <CardContent>
            <LineChart data={path} tone="primary" label="probability path" height={120} />
            <p className="mt-1 text-xs text-muted-foreground">
              Prior → posterior after each evidence item.
            </p>
          </CardContent>
        </Card>
      </div>

      <Card className="mt-4">
        <CardHeader className="flex-row items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Brain className="h-4 w-4" /> Evidence
          </CardTitle>
          <Button
            size="sm"
            variant="outline"
            onClick={() =>
              setEvidence((e) => [
                ...e,
                { label: `Evidence ${e.length + 1}`, ifTrue: 0.6, ifFalse: 0.4 },
              ])
            }
          >
            <Plus className="h-3.5 w-3.5" /> Add
          </Button>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <div className="grid grid-cols-[1fr_5rem_5rem_5rem_2rem] gap-2 text-[10px] uppercase tracking-wide text-muted-foreground">
              <span>Evidence</span>
              <span>P(E|H)</span>
              <span>P(E|¬H)</span>
              <span>LR</span>
              <span />
            </div>
            {evidence.map((row, i) => (
              <div key={i} className="grid grid-cols-[1fr_5rem_5rem_5rem_2rem] items-center gap-2">
                <input
                  value={row.label}
                  onChange={(e) => update(i, { label: e.target.value })}
                  className="h-8 rounded-md border bg-background px-2 text-sm"
                  aria-label="Evidence label"
                />
                <input
                  type="number"
                  min={0}
                  max={1}
                  step={0.05}
                  value={row.ifTrue}
                  onChange={(e) => update(i, { ifTrue: Number(e.target.value) })}
                  className="h-8 rounded-md border bg-background px-2 text-sm tabular-nums"
                  aria-label="P(E given H)"
                />
                <input
                  type="number"
                  min={0}
                  max={1}
                  step={0.05}
                  value={row.ifFalse}
                  onChange={(e) => update(i, { ifFalse: Number(e.target.value) })}
                  className="h-8 rounded-md border bg-background px-2 text-sm tabular-nums"
                  aria-label="P(E given not H)"
                />
                <span className="text-sm tabular-nums">
                  {steps[i]?.likelihoodRatio.toFixed(2) ?? "—"}
                </span>
                <button
                  onClick={() => setEvidence((e) => e.filter((_, idx) => idx !== i))}
                  aria-label="Remove evidence"
                  className="text-muted-foreground hover:text-loss"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </>
  );
}
