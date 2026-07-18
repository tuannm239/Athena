"use client";

import { Pin } from "lucide-react";
import { useUxStore } from "@/stores/ux-store";
import { cn } from "@/lib/utils";

/** Pin toggle for companies/tickers (Phase 6, WS7). Persisted locally. */
export function PinButton({ ticker, className }: { ticker: string; className?: string }) {
  const pinned = useUxStore((s) => s.isPinned(ticker));
  const toggle = useUxStore((s) => s.togglePin);
  return (
    <button
      type="button"
      onClick={() => toggle(ticker)}
      aria-pressed={pinned}
      aria-label={pinned ? `Unpin ${ticker}` : `Pin ${ticker}`}
      title={pinned ? `Unpin ${ticker}` : `Pin ${ticker}`}
      className={cn(
        "inline-flex h-8 w-8 items-center justify-center rounded-md transition-colors hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        className,
      )}
    >
      <Pin className={cn("h-4 w-4", pinned ? "fill-primary text-primary" : "text-muted-foreground")} />
    </button>
  );
}
