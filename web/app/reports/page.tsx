"use client";

import { useEffect, useMemo, useState } from "react";
import { CalendarDays, FileText } from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ExportMenu } from "@/components/export-menu";
import { useDecisions, usePortfolios } from "@/hooks/queries";
import { decisionColumns, positionColumns } from "@/lib/report-columns";
import type { Column } from "@/lib/export";
import type { DecisionResponse, PositionOut } from "@/types/api";
import { pct } from "@/lib/utils";

const riskColumns: Column<DecisionResponse>[] = [
  { header: "Decision", accessor: (d) => d.hypothesis },
  { header: "Risk level", accessor: (d) => d.risk_assessment?.level ?? "" },
  { header: "VaR", accessor: (d) => d.risk_assessment?.var ?? "" },
  { header: "CVaR", accessor: (d) => d.risk_assessment?.cvar ?? "" },
  { header: "Max drawdown", accessor: (d) => d.risk_assessment?.max_drawdown ?? "" },
  { header: "Stress", accessor: (d) => d.risk_assessment?.stress_score ?? "" },
  { header: "Liquidity", accessor: (d) => d.risk_assessment?.liquidity_score ?? "" },
  { header: "Probability", accessor: (d) => pct(d.probability) },
];

type PositionRow = PositionOut & { portfolio: string };
const portfolioReportColumns: Column<PositionRow>[] = [
  { header: "Portfolio", accessor: (p) => p.portfolio },
  ...positionColumns.map((c) => ({ header: c.header, accessor: (p: PositionRow) => c.accessor(p) })),
];

interface ReportDef {
  kind: string;
  title: string;
  description: string;
  time?: boolean;
}

const REPORTS: ReportDef[] = [
  { kind: "decision", title: "Decision Report", description: "All tracked decisions with probability, utility and risk." },
  { kind: "portfolio", title: "Portfolio Report", description: "Holdings and unrealized P&L across portfolios." },
  { kind: "risk", title: "Risk Report", description: "Risk assessments (VaR, CVaR, drawdown) per decision." },
  { kind: "backtest", title: "Backtest Report", description: "Historical strategy performance." },
  { kind: "scenario", title: "Scenario Report", description: "Scenario-simulation outcomes." },
  { kind: "daily", title: "Daily Report", description: "Decisions created in the last 24 hours.", time: true },
  { kind: "weekly", title: "Weekly Report", description: "Decisions created in the last 7 days.", time: true },
  { kind: "monthly", title: "Monthly Report", description: "Decisions created in the last 30 days.", time: true },
];

function withinDays(iso: string, days: number): boolean {
  const t = new Date(iso).getTime();
  return Number.isFinite(t) && Date.now() - t <= days * 86_400_000;
}

export default function ReportsPage() {
  const decisions = useDecisions({ limit: 100 });
  const portfolios = usePortfolios({ limit: 20 });
  const [highlight, setHighlight] = useState<string | null>(null);

  useEffect(() => {
    const kind = new URLSearchParams(window.location.search).get("kind");
    if (kind) {
      setHighlight(kind);
      document
        .getElementById(`report-${kind}`)
        ?.scrollIntoView({ block: "center", behavior: "smooth" });
    }
  }, []);

  const items = decisions.data?.items ?? [];
  const positions: PositionRow[] = useMemo(
    () =>
      (portfolios.data?.items ?? []).flatMap((p) =>
        p.positions.map((pos) => ({ ...pos, portfolio: p.id.slice(0, 8) })),
      ),
    [portfolios.data],
  );

  function menuFor(def: ReportDef) {
    const stamp = new Date().toISOString().slice(0, 10);
    const meta: [string, string][] = [["Report", def.title]];
    if (def.kind === "decision") {
      return (
        <ExportMenu
          filename={`athena-decision-report-${stamp}`}
          title={def.title}
          columns={decisionColumns}
          rows={items}
          pdf={{ orientation: "l", meta }}
        />
      );
    }
    if (def.kind === "risk") {
      const rows = items.filter((d) => d.risk_assessment);
      return (
        <ExportMenu
          filename={`athena-risk-report-${stamp}`}
          title={def.title}
          columns={riskColumns}
          rows={rows}
          pdf={{ orientation: "l", meta }}
        />
      );
    }
    if (def.kind === "portfolio") {
      return (
        <ExportMenu
          filename={`athena-portfolio-report-${stamp}`}
          title={def.title}
          columns={portfolioReportColumns}
          rows={positions}
          pdf={{ orientation: "l", meta }}
        />
      );
    }
    if (def.time) {
      const days = def.kind === "daily" ? 1 : def.kind === "weekly" ? 7 : 30;
      const rows = items.filter((d) => withinDays(d.created_at, days));
      return (
        <ExportMenu
          filename={`athena-${def.kind}-report-${stamp}`}
          title={def.title}
          columns={decisionColumns}
          rows={rows}
          pdf={{ orientation: "l", subtitle: `Window: last ${days} day(s)`, meta }}
        />
      );
    }
    // backtest / scenario — data source not yet exposed over REST
    return <Badge variant="muted">awaiting data feed</Badge>;
  }

  function countFor(def: ReportDef): number | null {
    if (def.kind === "decision") return items.length;
    if (def.kind === "risk") return items.filter((d) => d.risk_assessment).length;
    if (def.kind === "portfolio") return positions.length;
    if (def.time) {
      const days = def.kind === "daily" ? 1 : def.kind === "weekly" ? 7 : 30;
      return items.filter((d) => withinDays(d.created_at, days)).length;
    }
    return null;
  }

  return (
    <>
      <PageHeader
        title="Reports"
        description="Generate Decision, Portfolio, Risk and periodic reports as PDF, Excel, CSV or JSON. Everything is produced in your browser — nothing is uploaded."
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {REPORTS.map((def) => {
          const count = countFor(def);
          const Icon = def.time ? CalendarDays : FileText;
          return (
            <Card
              key={def.kind}
              id={`report-${def.kind}`}
              className={highlight === def.kind ? "ring-2 ring-primary" : undefined}
            >
              <CardHeader>
                <CardTitle className="flex items-center gap-2 normal-case">
                  <Icon className="h-4 w-4 text-muted-foreground" /> {def.title}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <p className="text-sm text-muted-foreground">{def.description}</p>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-muted-foreground">
                    {count === null ? "—" : `${count} row${count === 1 ? "" : "s"}`}
                  </span>
                  {menuFor(def)}
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </>
  );
}
