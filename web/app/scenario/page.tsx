"use client";

import { useMemo, useState } from "react";
import { FlaskConical } from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Stat } from "@/components/ui/stat";
import { Skeleton } from "@/components/ui/skeleton";
import { usePortfolios } from "@/hooks/queries";
import { scenarioImpact } from "@/lib/analysis";
import { money } from "@/lib/utils";

const PRESETS: { label: string; shock: number }[] = [
  { label: "Market crash −20%", shock: -0.2 },
  { label: "Correction −10%", shock: -0.1 },
  { label: "Pullback −5%", shock: -0.05 },
  { label: "Rally +10%", shock: 0.1 },
];

export default function ScenarioPage() {
  const { data, isLoading } = usePortfolios();
  const [shock, setShock] = useState(-0.1);

  const portfolio = data?.items[0];
  const marketValue = useMemo(
    () => (portfolio?.positions ?? []).reduce((s, p) => s + Number(p.market_value || 0), 0),
    [portfolio],
  );
  const cash = Number(portfolio?.cash ?? 0);
  const result = scenarioImpact({ marketValue, marketShock: shock, cash });

  return (
    <>
      <PageHeader
        title="Scenario Simulator"
        description="Stress-test the portfolio against a market shock (ALG-015). Long-only, no leverage — cash is preserved. A what-if aid; nothing is executed."
      />

      {isLoading ? (
        <Skeleton className="h-64 w-full" />
      ) : (
        <div className="grid gap-4 lg:grid-cols-3">
          <Card className="lg:col-span-1">
            <CardHeader>
              <CardTitle>Market shock</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <input
                type="range"
                min={-0.5}
                max={0.5}
                step={0.01}
                value={shock}
                onChange={(e) => setShock(Number(e.target.value))}
                className="w-full"
                aria-label="Market shock"
              />
              <Stat
                label="Applied shock"
                value={`${shock >= 0 ? "+" : ""}${(shock * 100).toFixed(0)}%`}
                valueClassName={shock >= 0 ? "text-gain" : "text-loss"}
              />
              <div className="flex flex-wrap gap-1">
                {PRESETS.map((p) => (
                  <button
                    key={p.label}
                    onClick={() => setShock(p.shock)}
                    className="rounded-full border px-2 py-1 text-xs hover:bg-accent"
                  >
                    {p.label}
                  </button>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FlaskConical className="h-4 w-4" /> Projected impact
              </CardTitle>
            </CardHeader>
            <CardContent>
              {marketValue === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No portfolio holdings to stress-test. Add positions to your portfolio first.
                </p>
              ) : (
                <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                  <Stat label="Before" value={money(result.before)} />
                  <Stat
                    label="After"
                    value={money(result.after)}
                    valueClassName={result.change >= 0 ? "text-gain" : "text-loss"}
                  />
                  <Stat
                    label="Change"
                    value={money(result.change)}
                    valueClassName={result.change >= 0 ? "text-gain" : "text-loss"}
                  />
                  <Stat
                    label="Change %"
                    value={`${(result.changePct * 100).toFixed(1)}%`}
                    valueClassName={result.change >= 0 ? "text-gain" : "text-loss"}
                  />
                </div>
              )}
              <p className="mt-3 text-xs text-muted-foreground">
                Equity portion shocked; cash ({money(cash)}) preserved. No derivatives or leverage
                are modelled.
              </p>
            </CardContent>
          </Card>
        </div>
      )}
    </>
  );
}
