"use client";

import Link from "next/link";
import { ShieldCheck } from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

const GUARANTEES = [
  "No automatic trading",
  "No broker integration",
  "Human approval mandatory",
  "No derivatives, no margin",
  "Full audit trail",
  "LLMs never produce decisions",
];

export default function AboutPage() {
  return (
    <>
      <PageHeader title="About Athena" description="Financial Decision Intelligence for the Vietnamese market." />

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Athena</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-muted-foreground">
            <p>
              Athena improves investment <strong>decision quality</strong> through explainable,
              probabilistic, risk-aware reasoning, optimized for long-term investing in the
              Vietnamese market (HOSE · HNX · UPCoM).
            </p>
            <p>
              It turns market data, fundamentals and evidence into <strong>Decision Objects</strong>{" "}
              for a human to review and approve. Athena assists; the investor decides.
            </p>
            <div className="flex flex-wrap gap-2 pt-2">
              <Badge variant="primary">Web v1.0</Badge>
              <Badge variant="muted">API v0.4.0</Badge>
              <Badge variant="muted">Vietnam Edition</Badge>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ShieldCheck className="h-4 w-4" /> Safety guarantees
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-1 text-sm">
              {GUARANTEES.map((g) => (
                <li key={g} className="flex items-center gap-2">
                  <span className="text-gain">✓</span> {g}
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      </div>

      <Card className="mt-4">
        <CardHeader>
          <CardTitle>Technology</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          <p>
            A modular monolith (DDD / Clean / Hexagonal): FastAPI + SQLAlchemy backend, Next.js /
            React frontend, PostgreSQL / DuckDB / Redis, behind an Nginx TLS edge with Prometheus,
            Grafana and Alertmanager. Every recommendation is explainable; every model backtestable;
            every business rule testable.
          </p>
          <p className="mt-2">
            See the <Link href="/release-notes" className="text-primary hover:underline">release notes</Link> and{" "}
            <Link href="/help" className="text-primary hover:underline">help center</Link>.
          </p>
        </CardContent>
      </Card>
    </>
  );
}
