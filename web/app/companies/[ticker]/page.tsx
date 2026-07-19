"use client";

import { use } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowLeft,
  CheckCircle2,
  Flag,
  Lightbulb,
  ShieldAlert,
  TrendingDown,
  TrendingUp,
} from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Stat } from "@/components/ui/stat";
import { Gauge } from "@/components/ui/gauge";
import { EmptyState } from "@/components/ui/empty-state";
import { FavoriteButton } from "@/components/ui/favorite-button";
import { PinButton } from "@/components/ui/pin-button";
import { companiesService } from "@/services/market";
import { vnFundamentalsService } from "@/services/vn-market";
import { useDecisions } from "@/hooks/queries";
import { useTrackRecent } from "@/hooks/use-track-recent";
import { ratioPct, vnd, type VnFundamentals } from "@/lib/vn";
import { pct } from "@/lib/utils";

/** Explainable bull/bear points derived from the fundamentals (transparent). */
function thesisPoints(f: VnFundamentals): { bull: string[]; bear: string[]; risks: string[] } {
  const r = f.ratios;
  const bull: string[] = [];
  const bear: string[] = [];
  const risks: string[] = [];
  if (r.roe !== null && r.roe >= 0.18) bull.push(`Strong ROE ${ratioPct(r.roe)}`);
  else if (r.roe !== null && r.roe < 0.05) bear.push(`Weak ROE ${ratioPct(r.roe)}`);
  if (r.net_margin !== null && r.net_margin >= 0.15) bull.push(`High net margin ${ratioPct(r.net_margin)}`);
  if (r.free_cash_flow !== null && r.free_cash_flow > 0) bull.push("Positive free cash flow");
  else if (r.free_cash_flow !== null) bear.push("Negative free cash flow");
  if (r.pe !== null && r.pe <= 10) bull.push(`Attractive P/E ${r.pe.toFixed(1)}`);
  else if (r.pe !== null && r.pe >= 25) bear.push(`Rich P/E ${r.pe.toFixed(1)}`);
  if (r.debt_to_equity !== null && r.debt_to_equity >= 2)
    risks.push(`Elevated leverage (D/E ${r.debt_to_equity.toFixed(2)})`);
  if (r.current_ratio !== null && r.current_ratio < 1)
    risks.push(`Liquidity risk (current ratio ${r.current_ratio.toFixed(2)})`);
  if (f.eps_growth_yoy !== null && f.eps_growth_yoy < 0)
    risks.push(`Declining EPS (${ratioPct(f.eps_growth_yoy)} YoY)`);
  if (bull.length === 0) bull.push("No standout strengths from current fundamentals");
  if (bear.length === 0) bear.push("No standout weaknesses from current fundamentals");
  if (risks.length === 0) risks.push("No elevated balance-sheet risks flagged");
  return { bull, bear, risks };
}

function List({
  title,
  icon: Icon,
  items,
  tone,
}: {
  title: string;
  icon: typeof Lightbulb;
  items: string[];
  tone: string;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className={`flex items-center gap-2 ${tone}`}>
          <Icon className="h-4 w-4" /> {title}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ul className="space-y-1 text-sm">
          {items.map((it, i) => (
            <li key={i} className="flex gap-2">
              <span className="text-muted-foreground">•</span>
              {it}
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}

export default function CompanyWorkspace({ params }: { params: Promise<{ ticker: string }> }) {
  const { ticker } = use(params);
  const T = ticker.toUpperCase();
  const company = useQuery({ queryKey: ["company", T], queryFn: () => companiesService.get(T) });
  const fund = useQuery({ queryKey: ["vn-fund", T], queryFn: () => vnFundamentalsService.get(T) });
  // Decisions are not ticker-keyed in the API; surface the latest few and let
  // the investor filter in the Decision Center. Matched heuristically by ticker
  // appearing in the hypothesis text.
  const decisions = useDecisions({ limit: 50 });

  useTrackRecent({ type: "company", id: T, label: T, href: `/companies/${T}` });

  const c = company.data?.data;
  const f = fund.data?.data;
  const related = (decisions.data?.items ?? []).filter((d) =>
    d.hypothesis.toUpperCase().includes(T),
  );
  const latest = related[0];
  const points = f ? thesisPoints(f) : null;

  return (
    <>
      <Link
        href="/companies"
        className="mb-3 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4" /> Companies
      </Link>
      <PageHeader
        title={c ? `${c.ticker} — ${c.name}` : T}
        description={c ? `${c.exchange} · ${c.sector} · ${c.industry}` : "Company workspace"}
        actions={
          <div className="flex items-center gap-1">
            {fund.data?.mocked ? <Badge variant="warn">sample</Badge> : null}
            <PinButton ticker={T} />
            <FavoriteButton item={{ type: "company", id: T, label: T, href: `/companies/${T}` }} />
          </div>
        }
      />

      {/* Fundamentals + scores */}
      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Fundamentals</CardTitle>
          </CardHeader>
          <CardContent>
            {fund.isLoading || !f ? (
              <Skeleton className="h-40 w-full" />
            ) : (
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4">
                <Stat label="ROE" value={ratioPct(f.ratios.roe)} />
                <Stat label="ROA" value={ratioPct(f.ratios.roa)} />
                <Stat label="Gross margin" value={ratioPct(f.ratios.gross_margin)} />
                <Stat label="Net margin" value={ratioPct(f.ratios.net_margin)} />
                <Stat label="D/E" value={f.ratios.debt_to_equity?.toFixed(2) ?? "—"} />
                <Stat label="Current ratio" value={f.ratios.current_ratio?.toFixed(2) ?? "—"} />
                <Stat label="EPS" value={vnd(f.ratios.eps)} />
                <Stat label="BVPS" value={vnd(f.ratios.bvps)} />
                <Stat label="P/E" value={f.ratios.pe?.toFixed(1) ?? "—"} />
                <Stat label="P/B" value={f.ratios.pb?.toFixed(2) ?? "—"} />
                <Stat label="EV/EBITDA" value={f.ratios.ev_ebitda?.toFixed(1) ?? "—"} />
                <Stat label="FCF" value={vnd(f.ratios.free_cash_flow)} />
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Quality Scores</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-wrap items-center justify-around gap-2">
            {f ? (
              <>
                <Gauge value={(f.quality_score ?? 0) / 100} label="quality" tone="gain" />
                <Gauge value={(f.valuation_score ?? 0) / 100} label="valuation" tone="primary" />
                <Gauge value={(f.growth_score ?? 0) / 100} label="growth" tone="warn" />
              </>
            ) : (
              <Skeleton className="h-24 w-full" />
            )}
          </CardContent>
        </Card>
      </div>

      {/* Investment thesis */}
      <h2 className="mb-2 mt-6 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
        Investment Thesis
      </h2>
      {latest ? (
        <Card className="mb-4">
          <CardContent className="p-4">
            <p className="text-sm">{latest.hypothesis}</p>
            <div className="mt-3 grid grid-cols-3 gap-4">
              <Stat label="Probability" value={pct(latest.probability)} />
              <Stat label="Confidence" value={pct(latest.confidence)} />
              <Stat label="Expected utility" value={latest.expected_utility ?? "—"} />
            </div>
            <Link
              href={`/decisions/${latest.id}`}
              className="mt-2 inline-block text-xs text-primary hover:underline"
            >
              Open decision →
            </Link>
          </CardContent>
        </Card>
      ) : (
        <Card className="mb-4">
          <CardContent className="p-4 text-sm text-muted-foreground">
            No decision linked to {T} yet. The bull/bear/risk points below are derived directly from
            the fundamentals to seed a thesis — create a decision in the Decision Center to record
            probability, confidence and expected utility (human approval required).
          </CardContent>
        </Card>
      )}

      {points ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <List title="Bull Case" icon={TrendingUp} items={points.bull} tone="text-gain" />
          <List title="Bear Case" icon={TrendingDown} items={points.bear} tone="text-loss" />
          <List title="Risks" icon={ShieldAlert} items={points.risks} tone="text-warn" />
          <List
            title="Catalysts"
            icon={Flag}
            items={[
              f && f.eps_growth_yoy !== null && f.eps_growth_yoy > 0
                ? `Earnings momentum (${ratioPct(f!.eps_growth_yoy)} EPS YoY)`
                : "Upcoming quarterly results",
              "AGM / dividend announcements",
              "Sector rotation & foreign flows",
            ]}
            tone="text-primary"
          />
        </div>
      ) : null}

      {/* Historical decisions */}
      <h2 className="mb-2 mt-6 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
        Historical Decisions
      </h2>
      <Card>
        <CardContent className="p-4">
          {related.length === 0 ? (
            <EmptyState
              icon={CheckCircle2}
              title="No decisions reference this ticker yet"
              description="Decisions mentioning the ticker in their hypothesis appear here."
            />
          ) : (
            <ul className="divide-y">
              {related.map((d) => (
                <li key={d.id} className="flex items-center justify-between gap-2 py-2">
                  <Link href={`/decisions/${d.id}`} className="min-w-0 flex-1 truncate hover:underline">
                    <span className="text-sm">{d.hypothesis}</span>
                  </Link>
                  <span className="text-xs tabular-nums text-muted-foreground">
                    P {pct(d.probability)}
                  </span>
                  <Badge variant="muted">{d.status}</Badge>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </>
  );
}
