"use client";

/**
 * Notification bell + dropdown panel (Phase 6, WS5). Shows the unread count
 * and lists in-app notifications with per-item read/dismiss and links.
 * Closes on outside-click and Escape; fully keyboard reachable.
 */
import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { AlertTriangle, Bell, CheckCheck, Info, ShieldAlert, X } from "lucide-react";
import { useNotificationStore, type Severity } from "@/stores/notification-store";
import { confirm } from "@/stores/confirm-store";
import { cn } from "@/lib/utils";

const SEVERITY_ICON: Record<Severity, typeof Info> = {
  info: Info,
  warn: AlertTriangle,
  error: ShieldAlert,
};
const SEVERITY_COLOR: Record<Severity, string> = {
  info: "text-primary",
  warn: "text-warn",
  error: "text-loss",
};

export function NotificationBell() {
  const [open, setOpen] = useState(false);
  const items = useNotificationStore((s) => s.items);
  const markRead = useNotificationStore((s) => s.markRead);
  const markAllRead = useNotificationStore((s) => s.markAllRead);
  const dismiss = useNotificationStore((s) => s.dismiss);
  const clearAll = useNotificationStore((s) => s.clearAll);
  const ref = useRef<HTMLDivElement>(null);

  const unread = items.filter((n) => !n.read).length;

  useEffect(() => {
    if (!open) return;
    function onDown(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => {
          setOpen((v) => !v);
          if (!open && unread > 0) markAllRead();
        }}
        className="relative inline-flex h-9 w-9 items-center justify-center rounded-md hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        aria-label={`Notifications${unread ? ` (${unread} unread)` : ""}`}
        aria-haspopup="true"
        aria-expanded={open}
      >
        <Bell className="h-4 w-4" />
        {unread > 0 ? (
          <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-loss px-1 text-[10px] font-semibold text-white">
            {unread > 9 ? "9+" : unread}
          </span>
        ) : null}
      </button>

      {open ? (
        <div
          className="absolute right-0 top-11 z-50 w-80 overflow-hidden rounded-lg border bg-card shadow-xl"
          role="menu"
          aria-label="Notifications"
        >
          <div className="flex items-center justify-between border-b px-3 py-2">
            <span className="text-sm font-semibold">Notifications</span>
            <div className="flex items-center gap-1">
              <button
                onClick={markAllRead}
                className="rounded p-1 text-muted-foreground hover:bg-accent"
                title="Mark all read"
                aria-label="Mark all read"
              >
                <CheckCheck className="h-4 w-4" />
              </button>
              {items.length > 0 ? (
                <button
                  onClick={async () => {
                    if (
                      await confirm({
                        title: "Clear all notifications?",
                        description: "This dismisses every notification in the list.",
                        confirmLabel: "Clear all",
                        destructive: true,
                      })
                    )
                      clearAll();
                  }}
                  className="rounded px-2 py-1 text-xs text-muted-foreground hover:bg-accent"
                >
                  Clear
                </button>
              ) : null}
            </div>
          </div>

          <div className="max-h-[60vh] overflow-y-auto">
            {items.length === 0 ? (
              <p className="px-3 py-8 text-center text-sm text-muted-foreground">
                You&apos;re all caught up.
              </p>
            ) : (
              <ul className="divide-y">
                {items.map((n) => {
                  const Icon = SEVERITY_ICON[n.severity];
                  const body = (
                    <div className="flex gap-2">
                      <Icon className={cn("mt-0.5 h-4 w-4 shrink-0", SEVERITY_COLOR[n.severity])} />
                      <div className="min-w-0 flex-1">
                        <p className="flex items-center gap-2 text-sm font-medium">
                          {n.title}
                          {!n.read ? (
                            <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
                          ) : null}
                        </p>
                        <p className="text-xs text-muted-foreground">{n.body}</p>
                      </div>
                    </div>
                  );
                  return (
                    <li key={n.id} className="group relative">
                      {n.href ? (
                        <Link
                          href={n.href}
                          onClick={() => {
                            markRead(n.id);
                            setOpen(false);
                          }}
                          className="block px-3 py-2.5 pr-8 hover:bg-accent/50"
                        >
                          {body}
                        </Link>
                      ) : (
                        <div className="px-3 py-2.5 pr-8">{body}</div>
                      )}
                      <button
                        onClick={() => dismiss(n.id)}
                        className="absolute right-2 top-2.5 rounded p-1 text-muted-foreground opacity-0 hover:bg-accent group-hover:opacity-100"
                        aria-label="Dismiss notification"
                      >
                        <X className="h-3.5 w-3.5" />
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}
