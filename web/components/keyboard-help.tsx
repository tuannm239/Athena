"use client";

/** Keyboard shortcuts help (Phase 6, WS1). Opens on "?"; Esc closes. */
import { useEffect } from "react";
import { X } from "lucide-react";
import { useCommandStore } from "@/stores/command-store";

const SHORTCUTS: [string, string][] = [
  ["⌘ / Ctrl + K", "Open command palette / global search"],
  ["?", "Show this help"],
  ["↑ ↓", "Move between results"],
  ["↵ Enter", "Open the selected result"],
  ["Esc", "Close palette / dialog"],
];

export function KeyboardHelp() {
  const open = useCommandStore((s) => s.helpOpen);
  const setOpen = useCommandStore((s) => s.setHelpOpen);

  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, setOpen]);

  if (!open) return null;
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-label="Keyboard shortcuts"
    >
      <div className="absolute inset-0 bg-black/50" onClick={() => setOpen(false)} />
      <div className="relative z-10 w-full max-w-sm rounded-xl border bg-card p-5 shadow-2xl">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold">Keyboard shortcuts</h2>
          <button
            onClick={() => setOpen(false)}
            aria-label="Close"
            className="rounded p-1 text-muted-foreground hover:bg-accent"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        <dl className="space-y-2">
          {SHORTCUTS.map(([keys, desc]) => (
            <div key={keys} className="flex items-center justify-between gap-4">
              <dt>
                <kbd className="rounded border bg-muted px-1.5 py-0.5 font-mono text-xs">{keys}</kbd>
              </dt>
              <dd className="text-right text-sm text-muted-foreground">{desc}</dd>
            </div>
          ))}
        </dl>
      </div>
    </div>
  );
}
