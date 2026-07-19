"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowDownRight, ArrowUpRight, TrendingUp } from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Gauge } from "@/components/ui/gauge";
import { Stat } from "@/components/ui/stat";
import { useMarketContext } from "@/hooks/queries";
import { vnMarketService } from "@/services/vn-market";
import { ratioPct, vnd, type MoverQuote } from "@/lib/vn";
import { cn } from "@/lib/utils";

function chg(pct: number): string {
  return `${pct >= 0 ? "+" : ""}${(pct * 100).toFixed(2)}%`;
}
function tone(pct: number): string {
  return pct > 0 ? "text-gain" : pct < 0 ? "text-loss" : "text-muted-foreground";
}

function MoverTable({ title, rows }: { title: string; rows: MoverQuote[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <ul className="divide-y text-sm">
          {rows.map((m) => (
            <li key={m.ticker} className="flex items-center justify-between gap-2 py-1.5">
              <span className="font-medium">{m.ticker}</span>
              <span className="tabular-nums text-muted-foreground">
                {m.price.toLocaleString("vi-VN")}
              </span>
              <span className={cn("w-16 text-right tabular-nums", tone(m.change_pct))}>
                {chg(m.change_pct)}
              </span>
              <span className="w-20 text-right text-xs tabular-nums text-muted-foreground">
                {(m.volume / 1e6).toFixed(1)}M
              </span>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}

export default function MarketPage() {
  const snap = useQuery({ queryKey: ["vn-snapshot"], queryFn: () => vnMarketService.snapshot() });
  const regime = useMarketContext();
  const s = snap.data?.data;
  const mocked = snap.data?.mocked || regime.data?.mocked;

  return (
    <>
      <PageHeader
        title="Vietnam Market"
        description="HOSE · HNX · UPCoM — indices, breadth, flows and movers for the Vietnamese market."
        actions={mocked ? <Badge variant="warn">sample data</Badge> : null}
      />

      {snap.isLoading || !s ? (
        <Skeleton className="h-64 w-full" />
      ) : (
        <div className="space-y-4">
          {/* Indices */}
          <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-5">
            {s.indices.map((i) => (
              <Card key={i.code}>
                <CardContent className="p-4">
                  <p className="text-xs uppercase tracking-wide text-muted-foreground">{i.code}</p>
                  <p className="text-xl font-semibold tabular-nums">
                    {i.value.toLocaleString("vi-VN")}
                  </p>
                  <p className={cn("text-xs tabular-nums", tone(i.change_pct))}>
                    {i.change >= 0 ? "+" : ""}
                    {i.change.toFixed(2)} ({chg(i.change_pct)})
                  </p>
                </CardContent>
              </Card>
            ))}
          </div>

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {/* Regime */}
            <Card>
              <CardHeader>
                <CardTitle>Market Regime</CardTitle>
              </CardHeader>
              <CardContent className="flex items-center justify-around">
                {regime.data ? (
                  <>
                    <Gauge value={Number(regime.data.data.confidence)} label="confidence" />
                    <Badge variant="primary">{regime.data.data.regime}</Badge>
                  </>
                ) : (
                  <Skeleton className="h-24 w-full" />
                )}
              </CardContent>
            </Card>

            {/* Breadth */}
            <Card>
              <CardHeader>
                <CardTitle>Market Breadth</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="mb-2 flex h-3 overflow-hidden rounded-full">
                  <span className="bg-gain" style={{ flex: s.breadth.advancers }} />
                  <span className="bg-muted-foreground" style={{ flex: s.breadth.unchanged }} />
                  <span className="bg-loss" style={{ flex: s.breadth.decliners }} />
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-gain">▲ {s.breadth.advancers}</span>
                  <span className="text-muted-foreground">● {s.breadth.unchanged}</span>
                  <span className="text-loss">▼ {s.breadth.decliners}</span>
                </div>
                <div className="mt-3 grid grid-cols-2 gap-2">
                  <Stat label="New highs" value={s.new_high} valueClassName="text-gain text-lg" />
                  <Stat label="New lows" value={s.new_low} valueClassName="text-loss text-lg" />
                </div>
              </CardContent>
            </Card>

            {/* Liquidity + flows */}
            <Card>
              <CardHeader>
                <CardTitle>Liquidity &amp; Flows</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Matched value</span>
                  <span className="tabular-nums">{vnd(s.liquidity_value)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Foreign net</span>
                  <span className={cn("tabular-nums", tone(s.foreign.net_value))}>
                    {s.foreign.net_value >= 0 ? "+" : ""}
                    {vnd(s.foreign.net_value)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Proprietary net</span>
                  <span className={cn("tabular-nums", tone(s.proprietary.net_value))}>
                    {s.proprietary.net_value >= 0 ? "+" : ""}
                    {vnd(s.proprietary.net_value)}
                  </span>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Sector heatmap */}
          <Card>
            <CardHeader>
              <CardTitle>Sector Heatmap</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4">
                {s.sector_heatmap.map((sec) => (
                  <div
                    key={sec.sector}
                    className={cn(
                      "flex items-center justify-between rounded-md border p-3 text-sm",
                      sec.change_pct > 0
                        ? "border-gain/40 bg-gain/10"
                        : sec.change_pct < 0
                          ? "border-loss/40 bg-loss/10"
                          : "",
                    )}
                  >
                    <span className="truncate">{sec.sector}</span>
                    <span className={cn("tabular-nums", tone(sec.change_pct))}>
                      {sec.change_pct > 0 ? (
                        <ArrowUpRight className="inline h-3 w-3" />
                      ) : sec.change_pct < 0 ? (
                        <ArrowDownRight className="inline h-3 w-3" />
                      ) : null}
                      {ratioPct(sec.change_pct, 1)}
                    </span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Movers */}
          <div className="grid gap-4 md:grid-cols-3">
            <MoverTable title="Top Gainers" rows={s.top_gainers} />
            <MoverTable title="Top Losers" rows={s.top_losers} />
            <MoverTable title="Top Volume" rows={s.top_volume} />
          </div>
        </div>
      )}

      {mocked ? (
        <p className="mt-4 flex items-center gap-2 text-xs text-muted-foreground">
          <TrendingUp className="h-3.5 w-3.5" /> VN market values are clearly-labelled sample data
          and populate automatically once the live feed is connected.
        </p>
      ) : null}
    </>
  );
}
