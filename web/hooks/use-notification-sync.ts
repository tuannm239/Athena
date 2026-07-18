"use client";

/**
 * Derives in-app notifications (Phase 6, WS5) from signals the app already
 * fetches — pending reviews, component health, and provider liveness — and
 * reconciles them into the notification store so resolved conditions clear
 * themselves. No new backend endpoints; no polling beyond the existing
 * queries. Mount once, in the app shell.
 */
import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { decisionsService } from "@/services/decisions";
import { marketService } from "@/services/market";
import { useHealth } from "@/hooks/queries";
import {
  useNotificationStore,
  type NotificationInput,
} from "@/stores/notification-store";

export function useNotificationSync(): void {
  const reconcile = useNotificationStore((s) => s.reconcile);

  const pending = useQuery({
    queryKey: ["decisions", { status: "UNDER_REVIEW", limit: 1 }],
    queryFn: () => decisionsService.list({ status: "UNDER_REVIEW", limit: 1 }),
    refetchInterval: 60_000,
  });
  const health = useHealth();
  const market = useQuery({
    queryKey: ["market-context"],
    queryFn: () => marketService.context(),
    refetchInterval: 120_000,
  });

  // Review reminders
  useEffect(() => {
    const total = pending.data?.total ?? 0;
    const inputs: NotificationInput[] =
      total > 0
        ? [
            {
              id: "review-pending",
              kind: "review",
              severity: "info",
              title: "Decisions awaiting your review",
              body: `${total} decision${total === 1 ? "" : "s"} in UNDER_REVIEW. Athena assists; you approve.`,
              href: "/decisions?status=UNDER_REVIEW",
            },
          ]
        : [];
    reconcile("review", inputs);
  }, [pending.data?.total, reconcile]);

  // System + pipeline alerts from component health
  useEffect(() => {
    if (!health.data) return;
    const comps = health.data.components;
    const system: NotificationInput[] = [];
    const pipeline: NotificationInput[] = [];
    for (const [name, status] of Object.entries(comps)) {
      if (status === "ok") continue;
      if (name === "snapshots") {
        pipeline.push({
          id: "pipeline-snapshots",
          kind: "pipeline",
          severity: "warn",
          title: "Data pipeline storage degraded",
          body: `Snapshot store reports: ${status}. Published datasets may be stale.`,
          href: "/reports",
        });
      } else {
        system.push({
          id: `system-${name}`,
          kind: "system",
          severity: name === "database" ? "error" : "warn",
          title: `${name} unavailable`,
          body: `Health check reports ${name}: ${status}.`,
        });
      }
    }
    reconcile("system", system);
    reconcile("pipeline", pipeline);
  }, [health.data, reconcile]);

  // Provider liveness (market feed running on sample data)
  useEffect(() => {
    const mocked = market.data?.mocked;
    const inputs: NotificationInput[] = mocked
      ? [
          {
            id: "provider-market-sample",
            kind: "provider",
            severity: "info",
            title: "Market data provider not live",
            body: "Showing clearly-labelled sample data until the live feed is connected.",
            href: "/market",
          },
        ]
      : [];
    reconcile("provider", inputs);
  }, [market.data?.mocked, reconcile]);
}
