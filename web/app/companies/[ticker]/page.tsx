"use client";

import { use, useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, CheckCircle2, Flag, ShieldAlert, TrendingDown, TrendingUp } from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Stat } from "@/components/ui/stat";
import { Gauge } from "@/components/ui/gauge";
import { EmptyState } from "@/components/ui/empty-state";
import { FavoriteButton } from "@/components/ui/favorite-button";
import { PinButton } from "@/components/ui/pin-button";
import { CandlestickChart } from "@/components/ui/candlestick-chart";
import { Tabs, type TabDef } from "@/components/ui/tabs";
import { EvidenceCard } from "@/components/ui/evidence-card";
import { RiskLevelBadge } from "@/components/ui/decision-status-badge";
import { NotesPanel } from "@/components/notes-panel";
import { companiesService } from "@/services/market";
import { vnCompanyPricesService, vnFundamentalsService } from "@/services/vn-market";
import { useDecisions } from "@/hooks/queries";
import { useTrackRecent } from "@/hooks/use-track-recent";
import { ratioPct, vnd, type VnFundamentals } from "@/lib/vn";
import { pct } from "@/lib/utils";

const PEERS = [
  { ticker: "HPG", pe: 8.7, roe: 0.171, quality: 78.5 },
  { ticker: "HSG", pe: 11.2, roe: 0.124, quality: 66.0 },
  { ticker: "NKG", pe: 9.8, roe: 0.138, quality: 69.4 },
];

const TABS: TabDef[] = [
  { id: "overview", label: "Overview" },
  { id: "financials", label: "Financial Statements" },
  { id: "ratios", label: "Ratios" },
  { id: "growth", label: "Growth" },
  { id: "valuation", label: "Valuation" },
  { id: "research", label: "Research" },
  { id: "evidence", label: "Evidence" },
  { id: "decision", label: "Decision" },
  { id: "risk", label: "Risk" },
  { id: "history", label: "History" },
  { id: "notes", label: "Notes" },
  { id: "peers", label: "Peers" },
];

// Trailing trading-session counts per range (≈21 sessions/month). ALL = full history.
const RANGES = { "1M": 21, "3M": 63, "6M": 126, "1Y": 252, "5Y": 1250, ALL: Infinity } as const;
type RangeKey = keyof typeof RANGES;
const RANGE_KEYS = Object.keys(RANGES) as RangeKey[];

function thesisPoints(f: VnFundamentals): { bull: string[]; bear: string[]; risks: string[] } {
  const r = f.ratios;
  const bull: string[] = [];
  const bear: string[] = [];
  const risks: string[] = [];
  if (r.roe !== null && r.roe >= 0.18) bull.push(`Strong ROE ${ratioPct(r.roe)}`);
  else if (r.roe !== null && r.roe < 0.05) bear.push(`Weak ROE ${ratioPct(r.roe)}`);
  if (r.net_margin !== null && r.net_margin >= 0.15)
    bull.push(`High net margin ${ratioPct(r.net_margin)}`);
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

function List({ title, items, tone }: { title: string; items: string[]; tone: string }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className={tone}>{title}</CardTitle>
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
  const [tab, setTab] = useState("overview");
  const [range, setRange] = useState<RangeKey>("1Y");
  const company = useQuery({ queryKey: ["company", T], queryFn: () => companiesService.get(T) });
  const fund = useQuery({ queryKey: ["vn-fund", T], queryFn: () => vnFundamentalsService.get(T) });
  const prices = useQuery({ queryKey: ["vn-prices", T], queryFn: () => vnCompanyPricesService.get(T) });
  const decisions = useDecisions({ limit: 50 });

  useTrackRecent({ type: "company", id: T, label: T, href: `/companies/${T}` });

  const c = company.data?.data;
  const f = fund.data?.data;
  const related = (decisions.data?.items ?? []).filter((d) => d.hypothesis.toUpperCase().includes(T));
  const latest = related[0];
  const evidence = related.flatMap((d) => d.evidence.map((e) => ({ e, id: d.id })));
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

      <Tabs tabs={TABS} active={tab} onChange={setTab} className="mb-4" />

      {fund.isLoading || !f ? (
        <Skeleton className="h-64 w-full" />
      ) : tab === "overview" ? (
        <div className="grid gap-4 lg:grid-cols-3">
          <Card className="lg:col-span-2">
            <CardHeader className="flex-row items-center justify-between">
              <CardTitle>Price</CardTitle>
              {prices.data && prices.data.points.length > 1 ? (
                <div className="flex items-center gap-1" role="group" aria-label="Time range">
                  {RANGE_KEYS.map((key) => (
                    <button
                      key={key}
                      type="button"
                      onClick={() => setRange(key)}
                      aria-pressed={range === key}
                      className={`rounded px-2 py-0.5 text-xs font-medium transition-colors ${
                        range === key
                          ? "bg-primary text-primary-foreground"
                          : "text-muted-foreground hover:bg-muted"
                      }`}
                    >
                      {key}
                    </button>
                  ))}
                </div>
              ) : null}
            </CardHeader>
            <CardContent>
              {prices.data && prices.data.points.length > 1 ? (
                <CandlestickChart
                  data={prices.data.points.slice(-RANGES[range]).map((p) => ({
                    open: p.open,
                    high: p.high,
                    low: p.low,
                    close: p.close,
                    volume: p.volume,
                  }))}
                  height={260}
                  label={`${T} daily candlesticks (${range})`}
                />
              ) : (
                <EmptyState
                  title="No price history yet"
                  description="Daily candles appear here once a market sync has run for this ticker."
                />
              )}
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Quality Scores</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-wrap items-center justify-around gap-2">
              <Gauge value={(f.quality_score ?? 0) / 100} label="quality" tone="gain" />
              <Gauge value={(f.valuation_score ?? 0) / 100} label="valuation" tone="primary" />
              <Gauge value={(f.growth_score ?? 0) / 100} label="growth" tone="warn" />
            </CardContent>
          </Card>
        </div>
      ) : tab === "financials" ? (
        <Card>
          <CardHeader>
            <CardTitle>Key figures</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4">
              <Stat label="EPS" value={vnd(f.ratios.eps)} />
              <Stat label="BVPS" value={vnd(f.ratios.bvps)} />
              <Stat label="Free cash flow" value={vnd(f.ratios.free_cash_flow)} />
              <Stat label="Net margin" value={ratioPct(f.ratios.net_margin)} />
              <Stat label="Gross margin" value={ratioPct(f.ratios.gross_margin)} />
              <Stat label="Operating margin" value={ratioPct(f.ratios.operating_margin)} />
            </div>
            <p className="mt-3 text-xs text-muted-foreground">
              Full quarterly/annual statements populate from the live filing feed; key
              statement-derived figures are shown here.
            </p>
          </CardContent>
        </Card>
      ) : tab === "ratios" ? (
        <Card>
          <CardHeader>
            <CardTitle>Ratios</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4">
              <Stat label="ROE" value={ratioPct(f.ratios.roe)} />
              <Stat label="ROA" value={ratioPct(f.ratios.roa)} />
              <Stat label="Gross margin" value={ratioPct(f.ratios.gross_margin)} />
              <Stat label="Operating margin" value={ratioPct(f.ratios.operating_margin)} />
              <Stat label="Net margin" value={ratioPct(f.ratios.net_margin)} />
              <Stat label="D/E" value={f.ratios.debt_to_equity?.toFixed(2) ?? "—"} />
              <Stat label="Current ratio" value={f.ratios.current_ratio?.toFixed(2) ?? "—"} />
              <Stat label="EV/EBITDA" value={f.ratios.ev_ebitda?.toFixed(1) ?? "—"} />
            </div>
          </CardContent>
        </Card>
      ) : tab === "growth" ? (
        <div className="grid gap-4 md:grid-cols-2">
          <Card>
            <CardContent className="p-4">
              <Stat
                label="Revenue growth (YoY)"
                value={ratioPct(f.revenue_growth_yoy)}
                valueClassName={(f.revenue_growth_yoy ?? 0) >= 0 ? "text-gain" : "text-loss"}
              />
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <Stat
                label="EPS growth (YoY)"
                value={ratioPct(f.eps_growth_yoy)}
                valueClassName={(f.eps_growth_yoy ?? 0) >= 0 ? "text-gain" : "text-loss"}
              />
            </CardContent>
          </Card>
          <Card className="md:col-span-2">
            <CardContent className="p-4">
              <Gauge value={(f.growth_score ?? 0) / 100} label="growth score" tone="warn" />
            </CardContent>
          </Card>
        </div>
      ) : tab === "valuation" ? (
        <div className="grid gap-4 md:grid-cols-3">
          <Card>
            <CardContent className="p-4">
              <Stat label="P/E" value={f.ratios.pe?.toFixed(1) ?? "—"} />
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <Stat label="P/B" value={f.ratios.pb?.toFixed(2) ?? "—"} />
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <Stat label="EV/EBITDA" value={f.ratios.ev_ebitda?.toFixed(1) ?? "—"} />
            </CardContent>
          </Card>
          <Card className="md:col-span-3">
            <CardContent className="flex justify-center p-4">
              <Gauge value={(f.valuation_score ?? 0) / 100} label="valuation score" tone="primary" />
            </CardContent>
          </Card>
        </div>
      ) : tab === "research" ? (
        <div>
          <p className="mb-3 text-sm text-muted-foreground">
            Company research notes and documents. See the{" "}
            <Link href="/research" className="text-primary hover:underline">
              full Research workspace
            </Link>{" "}
            for the evidence corpus.
          </p>
          <NotesPanel ticker={T} />
        </div>
      ) : tab === "evidence" ? (
        evidence.length === 0 ? (
          <EmptyState title="No evidence linked to this ticker yet" />
        ) : (
          <div className="space-y-2">
            {evidence.map(({ e, id }) => (
              <Link key={e.id} href={`/decisions/${id}`} className="block">
                <EvidenceCard evidence={e} />
              </Link>
            ))}
          </div>
        )
      ) : tab === "decision" ? (
        <div className="space-y-4">
          {latest ? (
            <Card>
              <CardContent className="p-4">
                <p className="text-sm">{latest.hypothesis}</p>
                <div className="mt-3 grid grid-cols-3 gap-4">
                  <Stat label="Probability" value={pct(latest.probability)} />
                  <Stat label="Confidence" value={pct(latest.confidence)} />
                  <Stat label="Expected utility" value={latest.expected_utility ?? "—"} />
                </div>
                <Link href={`/decisions/${latest.id}`} className="mt-2 inline-block text-xs text-primary hover:underline">
                  Open decision →
                </Link>
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardContent className="p-4 text-sm text-muted-foreground">
                No decision linked to {T} yet. The bull/bear/risk points are derived from the
                fundamentals to seed a thesis — create a decision in the Decision Center (human
                approval required).
              </CardContent>
            </Card>
          )}
          {points ? (
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              <List title="Bull Case" items={points.bull} tone="text-gain" />
              <List title="Bear Case" items={points.bear} tone="text-loss" />
              <List title="Risks" items={points.risks} tone="text-warn" />
              <List
                title="Catalysts"
                items={[
                  f.eps_growth_yoy !== null && f.eps_growth_yoy > 0
                    ? `Earnings momentum (${ratioPct(f.eps_growth_yoy)} EPS YoY)`
                    : "Upcoming quarterly results",
                  "AGM / dividend announcements",
                  "Sector rotation & foreign flows",
                ]}
                tone="text-primary"
              />
            </div>
          ) : null}
        </div>
      ) : tab === "risk" ? (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ShieldAlert className="h-4 w-4" /> Risk
            </CardTitle>
          </CardHeader>
          <CardContent>
            {latest?.risk_assessment ? (
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
                <Stat label="Level" value={<RiskLevelBadge level={latest.risk_assessment.level} />} />
                <Stat label="VaR" value={latest.risk_assessment.var} />
                <Stat label="CVaR" value={latest.risk_assessment.cvar} />
                <Stat label="Max drawdown" value={latest.risk_assessment.max_drawdown} />
                <Stat label="Stress" value={latest.risk_assessment.stress_score} />
                <Stat label="Liquidity" value={latest.risk_assessment.liquidity_score} />
              </div>
            ) : (
              <div className="space-y-1 text-sm">
                {(points?.risks ?? []).map((r, i) => (
                  <p key={i} className="flex items-center gap-2">
                    <TrendingDown className="h-4 w-4 text-warn" /> {r}
                  </p>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      ) : tab === "history" ? (
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
                    <span className="text-xs tabular-nums text-muted-foreground">P {pct(d.probability)}</span>
                    <Badge variant="muted">{d.status}</Badge>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      ) : tab === "notes" ? (
        <NotesPanel ticker={T} />
      ) : tab === "peers" ? (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-4 w-4" /> Peer Comparison
            </CardTitle>
          </CardHeader>
          <CardContent>
            <table className="w-full text-sm">
              <thead>
                <tr className="text-xs text-muted-foreground">
                  <th className="text-left font-normal">Ticker</th>
                  <th className="text-right font-normal">P/E</th>
                  <th className="text-right font-normal">ROE</th>
                  <th className="text-right font-normal">Quality</th>
                </tr>
              </thead>
              <tbody>
                {PEERS.map((p) => (
                  <tr key={p.ticker} className={p.ticker === T ? "font-semibold" : ""}>
                    <td className="py-1">
                      <Link href={`/companies/${p.ticker}`} className="hover:underline">
                        {p.ticker}
                      </Link>
                    </td>
                    <td className="py-1 text-right tabular-nums">{p.pe.toFixed(1)}</td>
                    <td className="py-1 text-right tabular-nums">{ratioPct(p.roe)}</td>
                    <td className="py-1 text-right tabular-nums">{p.quality.toFixed(0)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      ) : (
        <Flag className="hidden" />
      )}
    </>
  );
}
