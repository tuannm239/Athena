"use client";

import { AlertTriangle, CheckCircle2, Info, X } from "lucide-react";
import { useToastStore, type ToastKind } from "@/stores/toast-store";
import { cn } from "@/lib/utils";

const ICON: Record<ToastKind, typeof Info> = {
  success: CheckCircle2,
  error: AlertTriangle,
  info: Info,
};
const TONE: Record<ToastKind, string> = {
  success: "border-gain/40 text-gain",
  error: "border-loss/40 text-loss",
  info: "border-primary/40 text-primary",
};

/** Toast viewport (top-right). Announced politely to assistive tech. */
export function Toaster() {
  const toasts = useToastStore((s) => s.toasts);
  const dismiss = useToastStore((s) => s.dismiss);
  return (
    <div
      className="pointer-events-none fixed right-4 top-4 z-[60] flex w-full max-w-sm flex-col gap-2"
      role="region"
      aria-live="polite"
      aria-label="Notifications"
    >
      {toasts.map((t) => {
        const Icon = ICON[t.kind];
        return (
          <div
            key={t.id}
            role="status"
            className={cn(
              "pointer-events-auto flex items-start gap-2 rounded-lg border bg-card p-3 shadow-lg",
              TONE[t.kind],
            )}
          >
            <Icon className="mt-0.5 h-4 w-4 shrink-0" />
            <p className="flex-1 text-sm text-foreground">{t.message}</p>
            <button
              onClick={() => dismiss(t.id)}
              aria-label="Dismiss"
              className="text-muted-foreground hover:text-foreground"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        );
      })}
    </div>
  );
}
