"use client";

import Link from "next/link";
import { CalendarClock, Eye, Star } from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { PinButton } from "@/components/ui/pin-button";
import { useUxStore } from "@/stores/ux-store";
import { EVENT_LABELS, upcomingEvents, type CorporateEvent } from "@/lib/vn";
import { formatDate } from "@/lib/utils";

export default function WatchlistPage() {
  const pinned = useUxStore((s) => s.pinnedCompanies);
  const favorites = useUxStore((s) => s.favorites.filter((f) => f.type === "company"));

  // Merge pinned + favorited company tickers (unique).
  const tickers = Array.from(new Set([...pinned, ...favorites.map((f) => f.id.toUpperCase())]));

  const events: CorporateEvent[] = tickers
    .flatMap((t) => upcomingEvents(t).slice(0, 2))
    .sort((a, b) => a.date.localeCompare(b.date))
    .slice(0, 12);

  return (
    <>
      <PageHeader
        title="Watchlist"
        description="Your Vietnamese companies, with upcoming report, AGM and dividend reminders. Long-term focus — Athena assists; you decide."
      />

      {tickers.length === 0 ? (
        <EmptyState
          icon={Star}
          title="Your watchlist is empty"
          description="Pin companies from the Vietnam Market or a company workspace to follow them here."
        />
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Eye className="h-4 w-4" /> Followed companies ({tickers.length})
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="divide-y">
                {tickers.map((t) => (
                  <li key={t} className="flex items-center justify-between gap-2 py-2">
                    <Link href={`/companies/${t}`} className="font-medium hover:underline">
                      {t}
                    </Link>
                    <div className="flex items-center gap-1">
                      <Link
                        href={`/companies/${t}`}
                        className="text-xs text-primary hover:underline"
                      >
                        Workspace →
                      </Link>
                      <PinButton ticker={t} />
                    </div>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <CalendarClock className="h-4 w-4" /> Upcoming reminders
              </CardTitle>
            </CardHeader>
            <CardContent>
              {events.length === 0 ? (
                <EmptyState title="No upcoming events" />
              ) : (
                <ul className="divide-y">
                  {events.map((e) => (
                    <li key={`${e.ticker}-${e.kind}-${e.date}`} className="flex items-center justify-between gap-2 py-2">
                      <div className="min-w-0">
                        <p className="text-sm">
                          <Link href={`/companies/${e.ticker}`} className="font-medium hover:underline">
                            {e.ticker}
                          </Link>{" "}
                          · {e.label}
                        </p>
                      </div>
                      <div className="flex shrink-0 items-center gap-2">
                        <Badge variant="muted">{EVENT_LABELS[e.kind]}</Badge>
                        <span className="text-xs tabular-nums text-muted-foreground">
                          {formatDate(e.date)}
                        </span>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
              <p className="mt-3 text-xs text-muted-foreground">
                Dates are a rules-based projection of the Vietnamese filing cadence and will use the
                live corporate-actions feed once connected.
              </p>
            </CardContent>
          </Card>
        </div>
      )}
    </>
  );
}
