"use client";

import { Star } from "lucide-react";
import { useUxStore, type FavoriteItem } from "@/stores/ux-store";
import { cn } from "@/lib/utils";

/** Star toggle to favorite any entity (Phase 6, WS7). Persisted locally. */
export function FavoriteButton({ item, className }: { item: FavoriteItem; className?: string }) {
  const isFavorite = useUxStore((s) => s.isFavorite(item.type, item.id));
  const toggle = useUxStore((s) => s.toggleFavorite);
  return (
    <button
      type="button"
      onClick={() => toggle(item)}
      aria-pressed={isFavorite}
      aria-label={isFavorite ? "Remove from favorites" : "Add to favorites"}
      title={isFavorite ? "Remove from favorites" : "Add to favorites"}
      className={cn(
        "inline-flex h-8 w-8 items-center justify-center rounded-md transition-colors hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        className,
      )}
    >
      <Star className={cn("h-4 w-4", isFavorite ? "fill-warn text-warn" : "text-muted-foreground")} />
    </button>
  );
}
