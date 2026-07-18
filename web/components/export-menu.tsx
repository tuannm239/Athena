"use client";

/**
 * Export dropdown (Phase 6, WS6). Offers CSV / Excel / PDF / JSON for any
 * tabular data. Generation happens client-side (lib/export) — nothing is
 * uploaded. Closes on outside-click/Escape; keyboard reachable.
 */
import { useEffect, useRef, useState } from "react";
import { ChevronDown, Download, FileJson, FileSpreadsheet, FileText, Table2 } from "lucide-react";
import { buttonVariants } from "@/components/ui/button";
import { exportAs, type Column, type ExportFormat, type PdfOptions } from "@/lib/export";
import { cn } from "@/lib/utils";

export interface ExportMenuProps<T> {
  filename: string;
  title: string;
  columns: Column<T>[];
  rows: T[];
  json?: unknown;
  pdf?: PdfOptions;
  formats?: ExportFormat[];
  label?: string;
  disabled?: boolean;
}

const FORMAT_META: Record<ExportFormat, { label: string; icon: typeof FileText }> = {
  csv: { label: "CSV", icon: Table2 },
  xlsx: { label: "Excel (.xlsx)", icon: FileSpreadsheet },
  pdf: { label: "PDF", icon: FileText },
  json: { label: "JSON", icon: FileJson },
};

export function ExportMenu<T>({
  filename,
  title,
  columns,
  rows,
  json,
  pdf,
  formats = ["csv", "xlsx", "pdf", "json"],
  label = "Export",
  disabled,
}: ExportMenuProps<T>) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState<ExportFormat | null>(null);
  const ref = useRef<HTMLDivElement>(null);

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

  async function run(format: ExportFormat) {
    setBusy(format);
    try {
      await exportAs(format, { filename, title, columns, rows, json, pdf });
      setOpen(false);
    } catch (err) {
      // Keep the menu open and surface the failure inline.
      console.error("export failed", err);
      alert(`Export failed: ${(err as Error).message}`);
    } finally {
      setBusy(null);
    }
  }

  const isDisabled = disabled || rows.length === 0;

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((v) => !v)}
        disabled={isDisabled}
        className={cn(buttonVariants({ variant: "outline", size: "sm" }))}
        aria-haspopup="true"
        aria-expanded={open}
        title={isDisabled ? "Nothing to export" : "Export data"}
      >
        <Download className="h-3.5 w-3.5" /> {label}
        <ChevronDown className="h-3.5 w-3.5" />
      </button>
      {open ? (
        <div
          className="absolute right-0 top-10 z-50 w-48 overflow-hidden rounded-md border bg-card shadow-lg"
          role="menu"
        >
          {formats.map((f) => {
            const meta = FORMAT_META[f];
            const Icon = meta.icon;
            return (
              <button
                key={f}
                onClick={() => run(f)}
                disabled={busy !== null}
                role="menuitem"
                className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-accent disabled:opacity-50"
              >
                <Icon className="h-4 w-4 text-muted-foreground" />
                {meta.label}
                {busy === f ? <span className="ml-auto text-xs text-muted-foreground">…</span> : null}
              </button>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}
