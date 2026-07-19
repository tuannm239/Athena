"use client";

import Link from "next/link";
import { AlertTriangle, Bell, CheckCheck, Info, ShieldAlert } from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { useNotificationStore, type Severity } from "@/stores/notification-store";
import { confirm } from "@/stores/confirm-store";
import { formatDateTime } from "@/lib/utils";
import { cn } from "@/lib/utils";

const ICON: Record<Severity, typeof Info> = { info: Info, warn: AlertTriangle, error: ShieldAlert };
const TONE: Record<Severity, string> = { info: "text-primary", warn: "text-warn", error: "text-loss" };

export default function NotificationsPage() {
  const items = useNotificationStore((s) => s.items);
  const markRead = useNotificationStore((s) => s.markRead);
  const markAllRead = useNotificationStore((s) => s.markAllRead);
  const dismiss = useNotificationStore((s) => s.dismiss);
  const clearAll = useNotificationStore((s) => s.clearAll);

  return (
    <>
      <PageHeader
        title="Notifications"
        description="Review reminders, pipeline, provider and system alerts — in-app only."
        actions={
          items.length > 0 ? (
            <div className="flex gap-2">
              <Button size="sm" variant="outline" onClick={markAllRead}>
                <CheckCheck className="h-3.5 w-3.5" /> Mark all read
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={async () => {
                  if (
                    await confirm({
                      title: "Clear all notifications?",
                      confirmLabel: "Clear all",
                      destructive: true,
                    })
                  )
                    clearAll();
                }}
              >
                Clear all
              </Button>
            </div>
          ) : null
        }
      />

      {items.length === 0 ? (
        <EmptyState icon={Bell} title="You're all caught up" description="No notifications right now." />
      ) : (
        <div className="space-y-2">
          {items.map((n) => {
            const Icon = ICON[n.severity];
            return (
              <Card key={n.id}>
                <CardContent className="flex items-start gap-3 p-4">
                  <Icon className={cn("mt-0.5 h-5 w-5 shrink-0", TONE[n.severity])} />
                  <div className="min-w-0 flex-1">
                    <p className="flex items-center gap-2 font-medium">
                      {n.title}
                      {!n.read ? <span className="h-1.5 w-1.5 rounded-full bg-primary" /> : null}
                    </p>
                    <p className="text-sm text-muted-foreground">{n.body}</p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {formatDateTime(new Date(n.at).toISOString())}
                    </p>
                    <div className="mt-2 flex gap-3 text-xs">
                      {n.href ? (
                        <Link href={n.href} onClick={() => markRead(n.id)} className="text-primary hover:underline">
                          Open
                        </Link>
                      ) : null}
                      {!n.read ? (
                        <button onClick={() => markRead(n.id)} className="text-muted-foreground hover:underline">
                          Mark read
                        </button>
                      ) : null}
                      <button onClick={() => dismiss(n.id)} className="text-muted-foreground hover:underline">
                        Dismiss
                      </button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </>
  );
}
