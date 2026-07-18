"use client";

import { PageHeader } from "@/components/layout/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Gauge } from "@/components/ui/gauge";
import { Stat } from "@/components/ui/stat";
import { useMarketContext } from "@/hooks/queries";
import { pct } from "@/lib/utils";

export default function MarketPage() {
  const { data, isLoading } = useMarketContext();

  return (
    <>
      <PageHeader
        title="Market"
        description="Regime, breadth, liquidity and volatility (RFC-0025 MarketScore)."
        actions={data?.mocked ? <Badge variant="warn">sample data</Badge> : null}
      />

      {isLoading ? (
        <Skeleton className="h-64 w-full" />
      ) : data ? (
        <div className="grid gap-4 md:grid-cols-3">
          <Card className="md:col-span-1">
            <CardHeader>
              <CardTitle>Regime</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col items-center gap-3">
              <Gauge value={Number(data.data.confidence)} label="confidence" />
              <Badge variant="primary" className="text-sm">
                {data.data.regime}
              </Badge>
            </CardContent>
          </Card>

          <Card className="md:col-span-2">
            <CardHeader>
              <CardTitle>MarketScore Components (RFC-0025)</CardTitle>
            </CardHeader>
            <CardContent className="grid grid-cols-2 gap-6 md:grid-cols-4">
              <Stat label="Breadth" value={data.data.breadth_score} />
              <Stat label="Liquidity" value={data.data.liquidity_score} />
              <Stat label="Volatility" value={data.data.volatility_score} />
              <Stat label="Rotation" value={data.data.rotation_score} />
            </CardContent>
          </Card>
        </div>
      ) : null}

      {data?.mocked ? (
        <p className="mt-3 text-xs text-muted-foreground">
          VNINDEX / VN30 / sector heatmaps and the regime classifier require live market-data feeds
          (R1). This view shows sample values from the MockProvider and will populate automatically
          when <code>/market/context</code> serves real data. Confidence gauge: {pct(data.data.confidence)}.
        </p>
      ) : null}
    </>
  );
}
