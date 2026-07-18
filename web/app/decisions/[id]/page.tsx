"use client";

import Link from "next/link";
import { use } from "react";
import ReactMarkdown from "react-markdown";
import { ArrowLeft, Clock } from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Gauge } from "@/components/ui/gauge";
import { Stat } from "@/components/ui/stat";
import { EvidenceCard } from "@/components/ui/evidence-card";
import {
  DecisionStatusBadge,
  RiskLevelBadge,
} from "@/components/ui/decision-status-badge";
import { ReviewPanel } from "@/features/decisions/review-panel";
import { FavoriteButton } from "@/components/ui/favorite-button";
import { ExportMenu } from "@/components/export-menu";
import { evidenceColumns } from "@/lib/report-columns";
import { useDecision } from "@/hooks/queries";
import { useTrackRecent } from "@/hooks/use-track-recent";
import { formatDateTime, pct, num, signClass } from "@/lib/utils";

export default function DecisionDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { data: d, isLoading, isError } = useDecision(id);

  useTrackRecent(
    d ? { type: "decision", id: d.id, label: d.hypothesis, href: `/decisions/${d.id}` } : null,
  );

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-72" />
        <div className="grid gap-4 md:grid-cols-3">
          <Skeleton className="h-40" />
          <Skeleton className="h-40" />
          <Skeleton className="h-40" />
        </div>
      </div>
    );
  }

  if (isError || !d) {
    return (
      <Card>
        <CardContent className="p-8 text-center text-sm text-muted-foreground">
          Decision not found.{" "}
          <Link href="/decisions" className="text-primary hover:underline">
            Back to Decision Center
          </Link>
        </CardContent>
      </Card>
    );
  }

  const supporting = d.evidence.filter((e) => e.direction === "SUPPORTING");
  const contradicting = d.evidence.filter((e) => e.direction === "CONTRADICTING");
  const neutral = d.evidence.filter((e) => e.direction === "NEUTRAL");

  return (
    <>
      <Link
        href="/decisions"
        className="mb-3 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4" /> Decision Center
      </Link>
      <PageHeader
        title={d.hypothesis}
        description={`Created ${formatDateTime(d.created_at)}`}
        actions={
          <>
            <FavoriteButton
              item={{
                type: "decision",
                id: d.id,
                label: d.hypothesis,
                href: `/decisions/${d.id}`,
              }}
            />
            <DecisionStatusBadge status={d.status} />
          </>
        }
      />

      <div className="grid gap-4 lg:grid-cols-3">
        {/* Probability + confidence */}
        <Card>
          <CardHeader>
            <CardTitle>Probability &amp; Confidence</CardTitle>
          </CardHeader>
          <CardContent className="flex items-center justify-around">
            <Gauge value={Number(d.probability)} label="probability" tone="primary" />
            <Gauge value={Number(d.confidence)} label="confidence" tone="gain" />
          </CardContent>
        </Card>

        {/* Expected utility / return */}
        <Card>
          <CardHeader>
            <CardTitle>Expected Utility</CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-2 gap-4">
            <Stat
              label="Utility"
              value={num(d.expected_utility, 4)}
              valueClassName={signClass(d.expected_utility)}
            />
            <Stat label="Position size" value={pct(d.position_size)} />
            <Stat
              label="Exp. return"
              value={pct(d.expected_return)}
              valueClassName={signClass(d.expected_return)}
            />
            <Stat label="Exp. drawdown" value={pct(d.expected_drawdown)} valueClassName="text-loss" />
          </CardContent>
        </Card>

        {/* Risk */}
        <Card>
          <CardHeader>
            <CardTitle>Risk Assessment</CardTitle>
          </CardHeader>
          <CardContent>
            {d.risk_assessment ? (
              <div className="space-y-3">
                <RiskLevelBadge level={d.risk_assessment.level} />
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">VaR 95%</span>
                    <span className="tabular-nums">{pct(d.risk_assessment.var)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">CVaR 95%</span>
                    <span className="tabular-nums">{pct(d.risk_assessment.cvar)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Max DD</span>
                    <span className="tabular-nums">{pct(d.risk_assessment.max_drawdown)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Liquidity</span>
                    <span className="tabular-nums">{num(d.risk_assessment.liquidity_score, 0)}</span>
                  </div>
                </div>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No risk assessment attached.</p>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        {/* Evidence (2 cols) */}
        <div className="space-y-4 lg:col-span-2">
          <Card>
            <CardHeader className="flex-row items-center justify-between">
              <CardTitle>
                Evidence · {supporting.length} supporting · {contradicting.length} contradicting
                {neutral.length ? ` · ${neutral.length} neutral` : ""}
              </CardTitle>
              <ExportMenu
                filename={`athena-evidence-${d.id.slice(0, 8)}`}
                title="Athena — Evidence"
                columns={evidenceColumns}
                rows={d.evidence}
                pdf={{ subtitle: d.hypothesis, orientation: "l" }}
                label="Export"
              />
            </CardHeader>
            <CardContent className="space-y-2">
              {d.evidence.length === 0 ? (
                <p className="text-sm text-muted-foreground">No evidence recorded.</p>
              ) : (
                d.evidence.map((e) => <EvidenceCard key={e.id} evidence={e} />)
              )}
            </CardContent>
          </Card>

          {/* Explanation */}
          {d.explanation ? (
            <Card>
              <CardHeader>
                <CardTitle>Explanation</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="prose prose-sm prose-invert max-w-none text-sm">
                  <ReactMarkdown>{d.explanation}</ReactMarkdown>
                </div>
              </CardContent>
            </Card>
          ) : null}

          {/* Assumptions & invalidation */}
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Assumptions</CardTitle>
              </CardHeader>
              <CardContent>
                {d.assumptions.length ? (
                  <ul className="list-inside list-disc space-y-1 text-sm">
                    {d.assumptions.map((a, i) => (
                      <li key={i}>{a}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-muted-foreground">None.</p>
                )}
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Invalidation Conditions</CardTitle>
              </CardHeader>
              <CardContent>
                {d.invalidation_conditions.length ? (
                  <ul className="list-inside list-disc space-y-1 text-sm">
                    {d.invalidation_conditions.map((a, i) => (
                      <li key={i}>{a}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-muted-foreground">None.</p>
                )}
              </CardContent>
            </Card>
          </div>
        </div>

        {/* Review + audit trail */}
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Human Review</CardTitle>
            </CardHeader>
            <CardContent>
              <ReviewPanel decision={d} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Audit Trail</CardTitle>
            </CardHeader>
            <CardContent>
              {d.review_history.length ? (
                <ol className="space-y-3">
                  {d.review_history.map((r, i) => (
                    <li key={i} className="flex gap-2 text-sm">
                      <Clock className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
                      <div>
                        <Badge variant="muted">{r.outcome.replace("_", " ")}</Badge>
                        <p className="mt-1 text-xs text-muted-foreground">{formatDateTime(r.at)}</p>
                        {r.note ? <p className="mt-1">{r.note}</p> : null}
                      </div>
                    </li>
                  ))}
                </ol>
              ) : (
                <p className="text-sm text-muted-foreground">No review actions yet.</p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </>
  );
}
