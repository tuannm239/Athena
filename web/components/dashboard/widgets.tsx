"use client";

/**
 * Dashboard widgets (Phase 6, WS2). Each renders a Card and reads only data
 * the app already exposes (decisions, market context, health, portfolios)
 * plus local UX state. Derivations are pure (lib/dashboard.ts); no business
 * logic lives here.
 */
import Link from "next/link";
import {
  Activity as ActivityIcon,
  ArrowRight,
  Briefcase,
  ClipboardCheck,
  Sparkles,
  TrendingUp,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Stat } from "@/components/ui/stat";
import { Gauge } from "@/components/ui/gauge";
import { BarList } from "@/components/ui/bar-list";
import { EmptyState } from "@/components/ui/empty-state";
import { DecisionStatusBadge, RiskLevelBadge } from "@/components/ui/decision-status-badge";
import { EvidenceCard } from "@/components/ui/evidence-card";
import { useQuery } from "@tanstack/react-query";
import { useHealth, useMarketContext, usePortfolios } from "@/hooks/queries";
import { vnMarketService } from "@/services/vn-market";
import { ratioPct } from "@/lib/vn";
import { useUxStore } from "@/stores/ux-store";
import {
  DECISION_STATUSES,
  RISK_LEVELS,
  latestEvidence,
  probabilityHistogram,
  reviewActivities,
  riskLevelCounts,
  statusCounts,
} from "@/lib/dashboard";
import { formatDateTime, money, pct } from "@/lib/utils";
import type { DecisionResponse } from "@/types/api";

type DecisionsProp = { decisions: DecisionResponse[]; loading: boolean };

function Loading({ h = "h-24" }: { h?: string }) {
  return <Skeleton className={`${h} w-full`} />;
}

/* 1 — Market Overview */
export function MarketOverviewWidget() {
  const market = useMarketContext();
  const d = market.data?.data;
  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between">
        <CardTitle>Market Overview</CardTitle>
        {market.data?.mocked ? <Badge variant="warn">sample</Badge> : null}
      </CardHeader>
      <CardContent>
        {market.isLoading ? (
          <Loading />
        ) : d ? (
          <BarList
            data={[
              { label: "Liquidity", value: Math.round(Number(d.liquidity_score)), tone: "primary" },
              { label: "Breadth", value: Math.round(Number(d.breadth_score)), tone: "gain" },
              { label: "Volatility", value: Math.round(Number(d.volatility_score)), tone: "warn" },
              { label: "Rotation", value: Math.round(Number(d.rotation_score)), tone: "muted" },
            ]}
          />
        ) : (
          <EmptyState title="Market data unavailable" />
        )}
      </CardContent>
    </Card>
  );
}

/* VN indices strip (VNINDEX / VN30 / HNX) */
export function VnIndicesWidget() {
  const snap = useQuery({ queryKey: ["vn-snapshot"], queryFn: () => vnMarketService.snapshot() });
  const indices = (snap.data?.data.indices ?? []).filter((i) =>
    ["VNINDEX", "VN30", "HNXINDEX"].includes(String(i.code)),
  );
  return (
    <Card className="md:col-span-2 xl:col-span-3">
      <CardHeader className="flex-row items-center justify-between">
        <CardTitle>Vietnam Indices</CardTitle>
        {snap.data?.mocked ? <Badge variant="warn">sample</Badge> : null}
      </CardHeader>
      <CardContent>
        {snap.isLoading ? (
          <Loading />
        ) : (
          <div className="grid grid-cols-3 gap-4">
            {indices.map((i) => (
              <Link key={i.code} href="/market" className="block hover:opacity-80">
                <p className="text-xs uppercase tracking-wide text-muted-foreground">{i.code}</p>
                <p className="text-xl font-semibold tabular-nums">
                  {i.value.toLocaleString("vi-VN")}
                </p>
                <p
                  className={`text-xs tabular-nums ${i.change_pct >= 0 ? "text-gain" : "text-loss"}`}
                >
                  {i.change_pct >= 0 ? "+" : ""}
                  {(i.change_pct * 100).toFixed(2)}%
                </p>
              </Link>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

/* Sector heatmap */
export function SectorHeatmapWidget() {
  const snap = useQuery({ queryKey: ["vn-snapshot"], queryFn: () => vnMarketService.snapshot() });
  const heat = snap.data?.data.sector_heatmap ?? [];
  return (
    <Card>
      <CardHeader>
        <CardTitle>Market Heatmap</CardTitle>
      </CardHeader>
      <CardContent>
        {snap.isLoading ? (
          <Loading />
        ) : (
          <div className="grid grid-cols-2 gap-1.5">
            {heat.slice(0, 8).map((s) => (
              <div
                key={s.sector}
                className={`flex items-center justify-between rounded px-2 py-1 text-xs ${
                  s.change_pct > 0 ? "bg-gain/15" : s.change_pct < 0 ? "bg-loss/15" : "bg-muted"
                }`}
              >
                <span className="truncate">{s.sector}</span>
                <span className={s.change_pct >= 0 ? "text-gain" : "text-loss"}>
                  {ratioPct(s.change_pct, 1)}
                </span>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

/* Watchlist (pinned / favorited companies) */
export function WatchlistWidget() {
  const pinned = useUxStore((s) => s.pinnedCompanies);
  const favCompanies = useUxStore((s) => s.favorites.filter((f) => f.type === "company"));
  const tickers = Array.from(new Set([...pinned, ...favCompanies.map((f) => f.id.toUpperCase())]));
  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between">
        <CardTitle>Watchlist</CardTitle>
        <Link href="/watchlist" className="text-xs text-primary hover:underline">
          Manage
        </Link>
      </CardHeader>
      <CardContent>
        {tickers.length === 0 ? (
          <EmptyState title="No companies followed" description="Pin companies to watch them here." />
        ) : (
          <div className="flex flex-wrap gap-2">
            {tickers.slice(0, 12).map((t) => (
              <Link
                key={t}
                href={`/companies/${t}`}
                className="rounded-full border px-3 py-1 text-sm hover:bg-accent"
              >
                {t}
              </Link>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

/* 2 — Decision Summary */
export function DecisionSummaryWidget({ decisions, loading }: DecisionsProp) {
  const counts = statusCounts(decisions);
  return (
    <Card>
      <CardHeader>
        <CardTitle>Decision Summary</CardTitle>
      </CardHeader>
      <CardContent>
        {loading ? (
          <Loading />
        ) : (
          <>
            <Stat label="Tracked" value={decisions.length} />
            <div className="mt-3">
              <BarList
                data={DECISION_STATUSES.map((s) => ({
                  label: s.replace("_", " "),
                  value: counts[s],
                  tone: s === "APPROVED" ? "gain" : s === "REJECTED" ? "loss" : "primary",
                }))}
              />
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}

/* 3 — Pending Reviews */
export function PendingReviewsWidget({ decisions, loading }: DecisionsProp) {
  const pending = decisions.filter((d) => d.status === "UNDER_REVIEW");
  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between">
        <CardTitle className="flex items-center gap-2">
          <ClipboardCheck className="h-4 w-4" /> Pending Reviews
        </CardTitle>
        {pending.length ? <Badge variant="warn">{pending.length}</Badge> : null}
      </CardHeader>
      <CardContent>
        {loading ? (
          <Loading />
        ) : pending.length === 0 ? (
          <EmptyState title="No decisions awaiting review" description="You're all caught up." />
        ) : (
          <ul className="divide-y">
            {pending.slice(0, 5).map((d) => (
              <li key={d.id} className="py-2">
                <Link href={`/decisions/${d.id}`} className="block hover:underline">
                  <p className="truncate text-sm font-medium">{d.hypothesis}</p>
                  <p className="text-xs text-muted-foreground">
                    P {pct(d.probability)} · conf {pct(d.confidence)}
                  </p>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}

/* 4 — Portfolio Summary */
export function PortfolioSummaryWidget() {
  const portfolios = usePortfolios({ limit: 5 });
  const items = portfolios.data?.items ?? [];
  const positions = items.flatMap((p) => p.positions);
  const totalValue = positions.reduce((sum, p) => sum + Number(p.market_value || 0), 0);
  const totalPnl = positions.reduce((sum, p) => sum + Number(p.unrealized_pnl || 0), 0);
  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between">
        <CardTitle className="flex items-center gap-2">
          <Briefcase className="h-4 w-4" /> Portfolio Summary
        </CardTitle>
        <Link href="/portfolio" className="text-xs text-primary hover:underline">
          View
        </Link>
      </CardHeader>
      <CardContent>
        {portfolios.isLoading ? (
          <Loading />
        ) : items.length === 0 ? (
          <EmptyState title="No portfolios" description="Create a portfolio to see holdings." />
        ) : (
          <div className="grid grid-cols-2 gap-4">
            <Stat label="Portfolios" value={items.length} />
            <Stat label="Positions" value={positions.length} />
            <Stat label="Market value" value={money(totalValue)} />
            <Stat
              label="Unrealized P&L"
              value={money(totalPnl)}
              valueClassName={totalPnl >= 0 ? "text-gain" : "text-loss"}
            />
          </div>
        )}
      </CardContent>
    </Card>
  );
}

/* 5 — System Health */
export function SystemHealthWidget() {
  const health = useHealth();
  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between">
        <CardTitle>System Health</CardTitle>
        {health.data ? (
          <Badge variant={health.data.status === "ok" ? "gain" : "warn"}>
            {health.data.status.toUpperCase()}
          </Badge>
        ) : null}
      </CardHeader>
      <CardContent>
        {health.isLoading ? (
          <Loading />
        ) : health.data ? (
          <ul className="space-y-1 text-sm">
            {Object.entries(health.data.components).map(([k, v]) => (
              <li key={k} className="flex items-center justify-between">
                <span className="text-muted-foreground">{k}</span>
                <span className={v === "ok" ? "text-gain" : "text-warn"}>{v}</span>
              </li>
            ))}
          </ul>
        ) : (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <ActivityIcon className="h-4 w-4" /> health unavailable
          </div>
        )}
      </CardContent>
    </Card>
  );
}

/* 6 — Latest Evidence */
export function LatestEvidenceWidget({ decisions, loading }: DecisionsProp) {
  const refs = latestEvidence(decisions, 3);
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Sparkles className="h-4 w-4" /> Latest Evidence
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {loading ? (
          <Loading h="h-32" />
        ) : refs.length === 0 ? (
          <EmptyState title="No evidence yet" description="Evidence appears as decisions gather support." />
        ) : (
          refs.map((r) => (
            <Link key={r.evidence.id} href={`/decisions/${r.decisionId}`} className="block">
              <EvidenceCard evidence={r.evidence} />
            </Link>
          ))
        )}
      </CardContent>
    </Card>
  );
}

/* 7 — Market Regime */
export function MarketRegimeWidget() {
  const market = useMarketContext();
  const d = market.data?.data;
  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between">
        <CardTitle>Market Regime</CardTitle>
        {market.data?.mocked ? <Badge variant="warn">sample</Badge> : null}
      </CardHeader>
      <CardContent className="flex items-center justify-between gap-4">
        {market.isLoading ? (
          <Loading />
        ) : d ? (
          <>
            <Stat
              label="Regime"
              value={
                <span className="flex items-center gap-2">
                  <TrendingUp className="h-5 w-5 text-gain" /> {d.regime}
                </span>
              }
              sub={`as of ${formatDateTime(d.timestamp)}`}
            />
            <Gauge value={Number(d.confidence)} label="confidence" />
          </>
        ) : (
          <EmptyState title="Regime unavailable" />
        )}
      </CardContent>
    </Card>
  );
}

/* 8 — Risk Distribution */
export function RiskDistributionWidget({ decisions, loading }: DecisionsProp) {
  const counts = riskLevelCounts(decisions);
  const total = RISK_LEVELS.reduce((s, l) => s + counts[l], 0);
  return (
    <Card>
      <CardHeader>
        <CardTitle>Risk Distribution</CardTitle>
      </CardHeader>
      <CardContent>
        {loading ? (
          <Loading />
        ) : total === 0 ? (
          <EmptyState title="No risk assessments" description="Risk levels appear once decisions are assessed." />
        ) : (
          <div className="space-y-3">
            <div className="flex flex-wrap gap-2">
              {RISK_LEVELS.filter((l) => counts[l] > 0).map((l) => (
                <span key={l} className="flex items-center gap-1">
                  <RiskLevelBadge level={l} /> <span className="text-xs tabular-nums">{counts[l]}</span>
                </span>
              ))}
            </div>
            <BarList
              data={RISK_LEVELS.map((l) => ({
                label: l.replace("_", " "),
                value: counts[l],
                tone: l === "HIGH" || l === "CRITICAL" ? "loss" : l === "MODERATE" ? "warn" : "gain",
              }))}
            />
          </div>
        )}
      </CardContent>
    </Card>
  );
}

/* 9 — Probability Distribution */
export function ProbabilityDistributionWidget({ decisions, loading }: DecisionsProp) {
  const bins = probabilityHistogram(decisions, 5);
  const total = bins.reduce((s, b) => s + b.count, 0);
  return (
    <Card>
      <CardHeader>
        <CardTitle>Probability Distribution</CardTitle>
      </CardHeader>
      <CardContent>
        {loading ? (
          <Loading />
        ) : total === 0 ? (
          <EmptyState title="No decisions to chart" />
        ) : (
          <BarList data={bins.map((b) => ({ label: b.label, value: b.count, tone: "primary" }))} />
        )}
      </CardContent>
    </Card>
  );
}

/* 10 — Recent Activities */
export function RecentActivitiesWidget({ decisions, loading }: DecisionsProp) {
  const reviews = reviewActivities(decisions, 5);
  const recent = useUxStore((s) => s.recent);
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <ActivityIcon className="h-4 w-4" /> Recent Activities
        </CardTitle>
      </CardHeader>
      <CardContent>
        {loading ? (
          <Loading />
        ) : reviews.length === 0 && recent.length === 0 ? (
          <EmptyState title="No recent activity" description="Reviews and pages you open appear here." />
        ) : (
          <ul className="space-y-2 text-sm">
            {reviews.map((a) => (
              <li key={a.id}>
                <Link href={a.href} className="flex items-center justify-between gap-2 hover:underline">
                  <span className="min-w-0 flex-1 truncate">
                    <span className="font-medium">{a.label}</span> · {a.detail}
                  </span>
                  <span className="shrink-0 text-xs text-muted-foreground">
                    {formatDateTime(a.at)}
                  </span>
                </Link>
              </li>
            ))}
            {recent.slice(0, 3).map((r) => (
              <li key={`recent-${r.type}-${r.id}`}>
                <Link
                  href={r.href}
                  className="flex items-center justify-between gap-2 text-muted-foreground hover:underline"
                >
                  <span className="min-w-0 flex-1 truncate">Viewed {r.label}</span>
                  <ArrowRight className="h-3 w-3 shrink-0" />
                </Link>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
