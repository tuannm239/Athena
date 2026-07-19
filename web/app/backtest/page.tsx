"use client";

import { useMemo, useState } from "react";
import { PageHeader } from "@/components/layout/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Stat } from "@/components/ui/stat";
import { LineChart } from "@/components/ui/line-chart";
import { backtestBuyHold, samplePriceSeries } from "@/lib/analysis";
import { ratioPct } from "@/lib/vn";

export default function BacktestPage() {
  const [ticker, setTicker] = useState("HPG");
  const [years, setYears] = useState(2);
  const [seed, setSeed] = useState(7);

  const prices = useMemo(
    () => samplePriceSeries(25_000, Math.round(years * 252), seed),
    [years, seed],
  );
  const result = useMemo(() => backtestBuyHold(prices), [prices]);

  return (
    <>
      <PageHeader
        title="Backtest"
        description="Buy-and-hold simulation (long-only, no leverage) with SPEC-09 metrics. Computed live in the browser."
        actions={<Badge variant="warn">sample price path</Badge>}
      />

      <Card className="mb-4">
        <CardContent className="flex flex-wrap items-end gap-4 p-4">
          <div>
            <label className="mb-1 block text-xs text-muted-foreground">Ticker</label>
            <input
              value={ticker}
              onChange={(e) => setTicker(e.target.value.toUpperCase())}
              className="h-9 w-28 rounded-md border bg-background px-3 text-sm"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs text-muted-foreground">Years</label>
            <select
              value={years}
              onChange={(e) => setYears(Number(e.target.value))}
              className="h-9 rounded-md border bg-background px-3 text-sm"
            >
              {[1, 2, 3, 5].map((y) => (
                <option key={y} value={y}>
                  {y}
                </option>
              ))}
            </select>
          </div>
          <Button variant="outline" size="sm" onClick={() => setSeed((s) => s + 1)}>
            Resample path
          </Button>
        </CardContent>
      </Card>

      <Card className="mb-4">
        <CardHeader>
          <CardTitle>{ticker} — Equity Curve (start = 1.0)</CardTitle>
        </CardHeader>
        <CardContent>
          <LineChart
            data={result.equity}
            tone={result.totalReturn >= 0 ? "gain" : "loss"}
            label="equity curve"
            height={200}
          />
        </CardContent>
      </Card>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="p-4">
            <Stat
              label="Total return"
              value={ratioPct(result.totalReturn)}
              valueClassName={result.totalReturn >= 0 ? "text-gain" : "text-loss"}
            />
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <Stat label="CAGR" value={ratioPct(result.cagr)} />
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <Stat label="Max drawdown" value={ratioPct(result.maxDrawdown)} valueClassName="text-loss" />
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <Stat label="Volatility (ann.)" value={ratioPct(result.volatility)} />
          </CardContent>
        </Card>
      </div>

      <p className="mt-4 text-xs text-muted-foreground">
        The price path is a clearly-labelled reproducible sample until the live VN price feed is
        connected; the backtest maths (returns, CAGR, drawdown, volatility) are real and run on
        whatever series is provided.
      </p>
    </>
  );
}
