"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Building2, Search } from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useUxStore } from "@/stores/ux-store";

const POPULAR = ["VNM", "HPG", "FPT", "VCB", "MWG", "VIC", "MSN", "ACB", "SSI", "GAS"];

export default function CompaniesPage() {
  const router = useRouter();
  const [input, setInput] = useState("");
  const pinned = useUxStore((s) => s.pinnedCompanies);

  function open(ticker: string) {
    const t = ticker.trim().toUpperCase();
    if (t) router.push(`/companies/${t}`);
  }

  return (
    <>
      <PageHeader
        title="Companies"
        description="Search a listed Vietnamese company to open its full workspace — fundamentals, charts, research, evidence and decision history."
      />

      <form
        onSubmit={(e) => {
          e.preventDefault();
          open(input);
        }}
        className="mb-6 flex max-w-md gap-2"
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
        <Button type="submit">Open</Button>
      </form>

      {pinned.length > 0 ? (
        <Card className="mb-4">
          <CardHeader>
            <CardTitle>Your pinned companies</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {pinned.map((t) => (
                <Link
                  key={t}
                  href={`/companies/${t}`}
                  className="rounded-full border px-3 py-1 text-sm hover:bg-accent"
                >
                  {t}
                </Link>
              ))}
            </div>
          </CardContent>
        </Card>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Building2 className="h-4 w-4" /> Popular on HOSE
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            {POPULAR.map((t) => (
              <Link
                key={t}
                href={`/companies/${t}`}
                className="rounded-full border px-3 py-1 text-sm hover:bg-accent"
              >
                {t}
              </Link>
            ))}
          </div>
        </CardContent>
      </Card>
    </>
  );
}
