"use client";

import { useState } from "react";
import { Building2, Search } from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { Stat } from "@/components/ui/stat";
import { useCompany } from "@/hooks/queries";

export default function CompaniesPage() {
  const [input, setInput] = useState("");
  const [ticker, setTicker] = useState("");
  const { data, isLoading, isError } = useCompany(ticker);

  return (
    <>
      <PageHeader
        title="Company Explorer"
        description="Search a listed company to inspect its profile, factors and decision history."
      />

      <form
        onSubmit={(e) => {
          e.preventDefault();
          setTicker(input.trim().toUpperCase());
        }}
        className="mb-4 flex max-w-md gap-2"
        role="search"
      >
        <div className="relative flex-1">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <input
            aria-label="Ticker symbol"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ticker (e.g. VNM, HPG, FPT)"
            className="h-9 w-full rounded-md border bg-background pl-8 pr-3 text-sm uppercase focus-visible:ring-2 focus-visible:ring-ring"
          />
        </div>
        <Button type="submit">Search</Button>
      </form>

      {!ticker ? (
        <EmptyState
          icon={Building2}
          title="Search for a company"
          description="Enter a ticker symbol to load its profile."
        />
      ) : isLoading ? (
        <Skeleton className="h-48 w-full" />
      ) : isError ? (
        <EmptyState icon={Building2} title="Company not found" description={`No listing for ${ticker}.`} />
      ) : data ? (
        <Card>
          <CardHeader className="flex-row items-center justify-between">
            <div>
              <CardTitle className="text-base text-foreground normal-case">
                {data.data.name}
              </CardTitle>
              <p className="text-sm text-muted-foreground">
                {data.data.ticker} · {data.data.exchange}
              </p>
            </div>
            <div className="flex items-center gap-2">
              {data.mocked ? <Badge variant="warn">sample data</Badge> : null}
              <Badge variant={data.data.status === "active" ? "gain" : "muted"}>
                {data.data.status}
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="grid grid-cols-2 gap-6 md:grid-cols-4">
            <Stat label="Sector" value={<span className="text-base">{data.data.sector}</span>} />
            <Stat label="Industry" value={<span className="text-base">{data.data.industry}</span>} />
            <Stat label="Currency" value={<span className="text-base">{data.data.currency}</span>} />
            <Stat label="Exchange" value={<span className="text-base">{data.data.exchange}</span>} />
          </CardContent>
        </Card>
      ) : null}

      {data?.mocked ? (
        <p className="mt-3 text-xs text-muted-foreground">
          Fundamentals, factors, valuation and peer comparison are served by backend endpoints that
          return 501 until real market-data feeds land (R1 / RFC-0024). This view shows sample data
          and will populate automatically once those endpoints are live.
        </p>
      ) : null}
    </>
  );
}
