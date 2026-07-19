"use client";

import { PageHeader } from "@/components/layout/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

const RELEASES: { version: string; date: string; highlights: string[] }[] = [
  {
    version: "Web v1.0",
    date: "2026-07-19",
    highlights: [
      "Complete daily workflow in one app: login → market → company → research → decision → watchlist → portfolio → reports.",
      "Company Workspace with tabbed Overview / Financials / Ratios / Growth / Valuation / Research / Evidence / Decision / Risk / History / Notes / Peers.",
      "Evidence Center, Notifications, Help Center, About, Feedback and Release Notes pages.",
      "SaaS-grade UX: toasts, confirmation dialogs, command palette, global search, register flow.",
      "Reports (PDF/Excel/CSV/JSON), watchlist reminders, research notes with attachments and audit.",
    ],
  },
  {
    version: "Vietnam Edition (Phase 7)",
    date: "2026-07-19",
    highlights: [
      "VN market reference (HOSE/HNX/UPCoM, VNINDEX/VN30/HNX30), fundamentals & quality scores, corporate actions.",
      "Vietnam market dashboard, per-company workspace, watchlist with report/AGM/dividend reminders.",
    ],
  },
  {
    version: "Pilot v0.9 (Phase 5)",
    date: "2026-07-18",
    highlights: [
      "Production deployment (images, Nginx TLS edge, CI/CD + CVE scanning, observability).",
      "Pilot mode, first production data provider, security hardening.",
    ],
  },
];

const KNOWN_ISSUES = [
  "Some views use clearly-labelled sample data until the live Vietnamese feeds are connected.",
  "Backtest/Scenario reports await their REST data source.",
  "Notes, attachments and feedback are stored locally in the browser in this pilot.",
  "No OpenTelemetry tracing yet; correlation is via structured logs and request IDs.",
];

export default function ReleaseNotesPage() {
  return (
    <>
      <PageHeader title="Release Notes" description="What's new in Athena, and current known issues." />

      <div className="space-y-4">
        {RELEASES.map((r) => (
          <Card key={r.version}>
            <CardHeader className="flex-row items-center justify-between">
              <CardTitle className="normal-case">{r.version}</CardTitle>
              <Badge variant="muted">{r.date}</Badge>
            </CardHeader>
            <CardContent>
              <ul className="list-disc space-y-1 pl-5 text-sm text-muted-foreground">
                {r.highlights.map((h, i) => (
                  <li key={i}>{h}</li>
                ))}
              </ul>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card className="mt-4">
        <CardHeader>
          <CardTitle>Known issues</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="list-disc space-y-1 pl-5 text-sm text-muted-foreground">
            {KNOWN_ISSUES.map((k, i) => (
              <li key={i}>{k}</li>
            ))}
          </ul>
        </CardContent>
      </Card>
    </>
  );
}
