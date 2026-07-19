"use client";

import { useEffect } from "react";
import { Button } from "@/components/ui/button";
import { useConfirmStore } from "@/stores/confirm-store";

/** Renders the pending confirmation request (mounted once in the shell). */
export function ConfirmDialog() {
  const pending = useConfirmStore((s) => s.pending);
  const settle = useConfirmStore((s) => s.settle);

  useEffect(() => {
    if (!pending) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") settle(false);
      if (e.key === "Enter") settle(true);
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [pending, settle]);

  if (!pending) return null;
  return (
    <div
      className="fixed inset-0 z-[70] flex items-center justify-center p-4"
      role="alertdialog"
      aria-modal="true"
      aria-label={pending.title}
    >
      <div className="absolute inset-0 bg-black/50" onClick={() => settle(false)} />
      <div className="relative z-10 w-full max-w-sm rounded-xl border bg-card p-5 shadow-2xl">
        <h2 className="text-sm font-semibold">{pending.title}</h2>
        {pending.description ? (
          <p className="mt-2 text-sm text-muted-foreground">{pending.description}</p>
        ) : null}
        <div className="mt-4 flex justify-end gap-2">
          <Button variant="outline" size="sm" onClick={() => settle(false)}>
            {pending.cancelLabel ?? "Cancel"}
          </Button>
          <Button
            variant={pending.destructive ? "destructive" : "default"}
            size="sm"
            onClick={() => settle(true)}
            autoFocus
          >
            {pending.confirmLabel ?? "Confirm"}
          </Button>
        </div>
      </div>
    </div>
  );
}
