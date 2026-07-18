"use client";

import { useEffect } from "react";
import { useUxStore, type EntityType } from "@/stores/ux-store";

/**
 * Record a visited entity into the Recent Items list (Phase 6, WS7). Call
 * from a page/detail view once the entity's label is known. No-ops until a
 * non-empty label is provided so we never record a loading placeholder.
 */
export function useTrackRecent(
  item: { type: EntityType; id: string; label: string; href: string } | null,
): void {
  const push = useUxStore((s) => s.pushRecent);
  const enabled = !!item && !!item.label && !!item.id;
  const key = enabled ? `${item!.type}:${item!.id}:${item!.label}` : "";
  useEffect(() => {
    if (!enabled || !item) return;
    push({ type: item.type, id: item.id, label: item.label, href: item.href });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);
}
