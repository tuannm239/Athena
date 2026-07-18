"use client";

import { Briefcase } from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { Stat } from "@/components/ui/stat";
import { ExportMenu } from "@/components/export-menu";
import { usePortfolios } from "@/hooks/queries";
import { positionColumns } from "@/lib/report-columns";
import { money, num, signClass } from "@/lib/utils";

export default function PortfolioPage() {
  const { data, isLoading } = usePortfolios();
  const portfolio = data?.items[0];

  return (
    <>
      <PageHeader
        title="Portfolio"
        description="Holdings, allocation and risk exposure."
        actions={
          <ExportMenu
            filename="athena-portfolio"
            title="Athena — Portfolio"
            columns={positionColumns}
            rows={portfolio?.positions ?? []}
            pdf={{ orientation: "l" }}
          />
        }
      />

      {isLoading ? (
        <Skeleton className="h-64 w-full" />
      ) : !portfolio ? (
        <EmptyState
          icon={Briefcase}
          title="No portfolio yet"
          description="Create a portfolio to track holdings and allocation."
        />
      ) : (
        <>
          <div className="mb-4 grid grid-cols-2 gap-4 md:grid-cols-4">
            <Card>
              <CardContent className="p-4">
                <Stat label="Cash" value={money(portfolio.cash, portfolio.base_currency)} />
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <Stat label="Positions" value={portfolio.positions.length} />
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <Stat label="Allocation" value={`${num(Number(portfolio.allocation) * 100, 1)}%`} />
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <Stat label="Base currency" value={portfolio.base_currency} />
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Holdings</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              {portfolio.positions.length === 0 ? (
                <p className="p-4 text-sm text-muted-foreground">No open positions.</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="border-b text-left text-xs uppercase text-muted-foreground">
                      <tr>
                        <th className="p-3">Ticker</th>
                        <th className="p-3 text-right">Quantity</th>
                        <th className="p-3 text-right">Avg cost</th>
                        <th className="p-3 text-right">Market value</th>
                        <th className="p-3 text-right">Unrealised P&amp;L</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y">
                      {portfolio.positions.map((p) => (
                        <tr key={p.ticker} className="hover:bg-accent/50">
                          <td className="p-3 font-medium">{p.ticker}</td>
                          <td className="p-3 text-right tabular-nums">{num(p.quantity, 0)}</td>
                          <td className="p-3 text-right tabular-nums">
                            {money(p.average_cost, p.currency)}
                          </td>
                          <td className="p-3 text-right tabular-nums">
                            {money(p.market_value, p.currency)}
                          </td>
                          <td className={`p-3 text-right tabular-nums ${signClass(p.unrealized_pnl)}`}>
                            {money(p.unrealized_pnl, p.currency)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </>
  );
}
