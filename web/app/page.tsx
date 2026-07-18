"use client";

import Link from "next/link";
import { Activity, ArrowRight, ShieldAlert, TrendingUp } from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Stat } from "@/components/ui/stat";
import { Gauge } from "@/components/ui/gauge";
import { DecisionStatusBadge } from "@/components/ui/decision-status-badge";
import { EmptyState } from "@/components/ui/empty-state";
import { useDecisions, useHealth, useMarketContext } from "@/hooks/queries";
import { formatDate, pct } from "@/lib/utils";

export default function DashboardPage() {
  const decisions = useDecisions({ limit: 5 });
  const market = useMarketContext();
  const health = useHealth();

  return (
    <>
      <PageHeader
        title="Dashboard"
        description="Decision intelligence at a glance. Athena assists; you approve."
      />

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        {/* Decision summary */}
        <Card>
          <CardHeader>
            <CardTitle>Decisions</CardTitle>
          </CardHeader>
          <CardContent>
            {decisions.isLoading ? (
              <Skeleton className="h-12 w-24" />
            ) : (
              <Stat
                label="Total tracked"
                value={decisions.data?.total ?? 0}
                sub={<span className="text-muted-foreground">across all lifecycle states</span>}
              />
            )}
          </CardContent>
        </Card>

        {/* Market regime */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              Market Regime
              {market.data?.mocked ? <Badge variant="warn">sample</Badge> : null}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {market.isLoading ? (
              <Skeleton className="h-12 w-32" />
            ) : market.data ? (
              <Stat
                label={market.data.data.regime}
                value={<TrendingUp className="inline h-6 w-6 text-gain" />}
                sub={<span>Confidence {pct(market.data.data.confidence)}</span>}
              />
            ) : null}
          </CardContent>
        </Card>

        {/* Regime confidence gauge */}
        <Card>
          <CardHeader>
            <CardTitle>Regime Confidence</CardTitle>
          </CardHeader>
          <CardContent className="flex justify-center">
            {market.isLoading ? (
              <Skeleton className="h-[120px] w-[120px] rounded-full" />
            ) : (
              <Gauge value={Number(market.data?.data.confidence ?? 0)} label="confidence" />
            )}
          </CardContent>
        </Card>

        {/* System health */}
        <Card>
          <CardHeader>
            <CardTitle>System Health</CardTitle>
          </CardHeader>
          <CardContent>
            {health.isLoading ? (
              <Skeleton className="h-12 w-24" />
            ) : health.data ? (
              <div className="space-y-2">
                <Badge variant={health.data.status === "ok" ? "gain" : "warn"}>
                  {health.data.status.toUpperCase()}
                </Badge>
                <ul className="space-y-1 text-xs text-muted-foreground">
                  {Object.entries(health.data.components).map(([k, v]) => (
                    <li key={k} className="flex justify-between">
                      <span>{k}</span>
                      <span className={v === "ok" ? "text-gain" : "text-warn"}>{v}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ) : (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Activity className="h-4 w-4" /> health unavailable
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Latest decisions */}
      <Card className="mt-4">
        <CardHeader className="flex-row items-center justify-between">
          <CardTitle>Latest Decisions</CardTitle>
          <Link
            href="/decisions"
            className="flex items-center gap-1 text-xs text-primary hover:underline"
          >
            View all <ArrowRight className="h-3 w-3" />
          </Link>
        </CardHeader>
        <CardContent>
          {decisions.isLoading ? (
            <div className="space-y-2">
              {[0, 1, 2].map((i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : decisions.data && decisions.data.items.length > 0 ? (
            <ul className="divide-y">
              {decisions.data.items.map((d) => (
                <li key={d.id} className="flex items-center justify-between gap-3 py-2">
                  <Link href={`/decisions/${d.id}`} className="min-w-0 flex-1 hover:underline">
                    <p className="truncate text-sm font-medium">{d.hypothesis}</p>
                    <p className="text-xs text-muted-foreground">{formatDate(d.created_at)}</p>
                  </Link>
                  <span className="text-sm tabular-nums text-muted-foreground">
                    P {pct(d.probability)}
                  </span>
                  <DecisionStatusBadge status={d.status} />
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState
              icon={ShieldAlert}
              title="No decisions yet"
              description="Create a decision in the Decision Center to begin tracking hypotheses."
            />
          )}
        </CardContent>
      </Card>
    </>
  );
}
