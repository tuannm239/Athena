"use client";

import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { buttonVariants } from "@/components/ui/button";
import { useDecisions } from "@/hooks/queries";
import { cn } from "@/lib/utils";
import {
  DecisionSummaryWidget,
  LatestEvidenceWidget,
  MarketOverviewWidget,
  MarketRegimeWidget,
  PendingReviewsWidget,
  PortfolioSummaryWidget,
  ProbabilityDistributionWidget,
  RecentActivitiesWidget,
  RiskDistributionWidget,
  SectorHeatmapWidget,
  SystemHealthWidget,
  VnIndicesWidget,
  WatchlistWidget,
} from "@/components/dashboard/widgets";

export default function DashboardPage() {
  const decisions = useDecisions({ limit: 50 });
  const items = decisions.data?.items ?? [];
  const loading = decisions.isLoading;
  const d = { decisions: items, loading };

  return (
    <>
      <PageHeader
        title="Dashboard"
        description="Decision intelligence at a glance. Athena assists; you approve."
        actions={
          <Link href="/decisions" className={cn(buttonVariants({ variant: "outline", size: "sm" }))}>
            Decision Center <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        }
      />

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        <VnIndicesWidget />

        <PortfolioSummaryWidget />
        <PendingReviewsWidget {...d} />
        <WatchlistWidget />

        <DecisionSummaryWidget {...d} />
        <SectorHeatmapWidget />
        <MarketRegimeWidget />

        <ProbabilityDistributionWidget {...d} />
        <RiskDistributionWidget {...d} />
        <SystemHealthWidget />

        <MarketOverviewWidget />
        <RecentActivitiesWidget {...d} />
        <div className="md:col-span-2 xl:col-span-1">
          <LatestEvidenceWidget {...d} />
        </div>
      </div>
    </>
  );
}
