"use client";

import Link from "next/link";
import { LifeBuoy, Keyboard, MessageSquare, FileText, BookOpen } from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useCommandStore } from "@/stores/command-store";

const FAQ: [string, string][] = [
  ["Does Athena trade for me?", "No. Athena is decision support only — it produces Decision Objects for you to approve. It executes no trades and connects to no broker."],
  ["What does the ‘sample’ badge mean?", "The live Vietnamese market feed for that view is not connected yet, so Athena shows clearly-labelled sample data. It populates automatically once the feed is live."],
  ["How do I analyze a company?", "Open Companies, search a ticker (or pick a popular/pinned one), and its workspace shows fundamentals, charts, ratios, research, evidence and decision history."],
  ["How do I export a report?", "Go to Reports and pick a report; export to PDF, Excel, CSV or JSON. Export is also available on Decisions, Portfolio and Evidence."],
  ["Is my data uploaded?", "Notes, attachments, watchlist and preferences are stored locally in your browser. Decisions and evidence live in the backend system of record."],
];

const SHORTCUTS: [string, string][] = [
  ["⌘ / Ctrl + K", "Command palette & global search"],
  ["?", "Keyboard shortcuts"],
  ["↑ ↓ / Enter / Esc", "Navigate / open / close"],
];

export default function HelpPage() {
  const openHelp = useCommandStore((s) => s.setHelpOpen);
  return (
    <>
      <PageHeader
        title="Help Center"
        description="Guides, FAQ, shortcuts and how to reach us."
        actions={
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <LifeBuoy className="h-4 w-4" /> Athena support
          </div>
        }
      />

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BookOpen className="h-4 w-4" /> User guide
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-muted-foreground">
            <p>
              Athena runs the whole daily loop in one place: review the Vietnam market, open a company
              workspace, read research, review Athena&apos;s recommendation, save it to your watchlist,
              check your portfolio, and export a report.
            </p>
            <p>Full guides ship with the product under <code>docs/product/</code> and <code>USER_GUIDE.md</code>.</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Keyboard className="h-4 w-4" /> Keyboard shortcuts
            </CardTitle>
          </CardHeader>
          <CardContent>
            <dl className="space-y-2">
              {SHORTCUTS.map(([k, v]) => (
                <div key={k} className="flex items-center justify-between gap-4 text-sm">
                  <dt>
                    <kbd className="rounded border bg-muted px-1.5 py-0.5 font-mono text-xs">{k}</kbd>
                  </dt>
                  <dd className="text-right text-muted-foreground">{v}</dd>
                </div>
              ))}
            </dl>
            <button
              onClick={() => openHelp(true)}
              className="mt-3 text-xs text-primary hover:underline"
            >
              Open shortcuts overlay
            </button>
          </CardContent>
        </Card>
      </div>

      <Card className="mt-4">
        <CardHeader>
          <CardTitle>Frequently asked questions</CardTitle>
        </CardHeader>
        <CardContent className="divide-y">
          {FAQ.map(([q, a]) => (
            <details key={q} className="py-2">
              <summary className="cursor-pointer text-sm font-medium">{q}</summary>
              <p className="mt-1 text-sm text-muted-foreground">{a}</p>
            </details>
          ))}
        </CardContent>
      </Card>

      <div className="mt-4 flex flex-wrap gap-3 text-sm">
        <Link href="/feedback" className="flex items-center gap-1 text-primary hover:underline">
          <MessageSquare className="h-4 w-4" /> Send feedback
        </Link>
        <Link href="/release-notes" className="flex items-center gap-1 text-primary hover:underline">
          <FileText className="h-4 w-4" /> Release notes & known issues
        </Link>
        <Link href="/about" className="flex items-center gap-1 text-primary hover:underline">
          About Athena
        </Link>
      </div>
    </>
  );
}
