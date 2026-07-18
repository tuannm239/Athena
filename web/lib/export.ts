/**
 * Export + report generation (Phase 6, WS6/WS3). Client-side only —
 * everything is produced in the browser from data already fetched, so no
 * backend endpoints are added and nothing is uploaded anywhere.
 *
 * Formats: JSON and CSV are native (zero deps); Excel (.xlsx) uses
 * write-excel-file and PDF uses jspdf + jspdf-autotable, both loaded via
 * dynamic import so they stay out of the initial bundle and never run on
 * the server.
 */

export interface Column<T> {
  header: string;
  accessor: (row: T) => string | number | null | undefined;
}

function triggerDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export function exportJSON(filename: string, data: unknown): void {
  triggerDownload(
    new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }),
    ensureExt(filename, "json"),
  );
}

function csvCell(value: unknown): string {
  const s = value === null || value === undefined ? "" : String(value);
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

export function toCSV<T>(columns: Column<T>[], rows: T[]): string {
  const head = columns.map((c) => csvCell(c.header)).join(",");
  const body = rows.map((r) => columns.map((c) => csvCell(c.accessor(r))).join(",")).join("\n");
  return `${head}\n${body}\n`;
}

export function exportCSV<T>(filename: string, columns: Column<T>[], rows: T[]): void {
  // Prepend a UTF-8 BOM so Excel opens accented text correctly.
  triggerDownload(
    new Blob(["﻿" + toCSV(columns, rows)], { type: "text/csv;charset=utf-8" }),
    ensureExt(filename, "csv"),
  );
}

export async function exportExcel<T>(
  filename: string,
  columns: Column<T>[],
  rows: T[],
): Promise<void> {
  const mod = await import("write-excel-file/browser");
  // The library's overloaded types don't cooperate with our generic; the
  // runtime shape (objects + schema + fileName) is correct, so cast the fn.
  const writeXlsxFile = mod.default as unknown as (
    data: T[],
    opts: { schema: unknown[]; fileName: string },
  ) => Promise<void>;
  const schema = columns.map((c) => ({
    column: c.header,
    type: String,
    value: (row: T) => {
      const v = c.accessor(row);
      return v === null || v === undefined ? "" : String(v);
    },
  }));
  await writeXlsxFile(rows, { schema, fileName: ensureExt(filename, "xlsx") });
}

export interface PdfOptions {
  subtitle?: string;
  /** Extra "key: value" lines printed under the title (report metadata). */
  meta?: [string, string][];
  orientation?: "p" | "l";
}

export async function exportPDF<T>(
  filename: string,
  title: string,
  columns: Column<T>[],
  rows: T[],
  options: PdfOptions = {},
): Promise<void> {
  const { jsPDF } = await import("jspdf");
  const autoTable = (await import("jspdf-autotable")).default;
  const doc = new jsPDF({ orientation: options.orientation ?? "p" });

  doc.setFontSize(16);
  doc.text(title, 14, 18);
  let y = 25;
  doc.setFontSize(9);
  doc.setTextColor(120);
  doc.text("ATHENA — Financial Decision Intelligence · decision support only", 14, y);
  y += 5;
  if (options.subtitle) {
    doc.text(options.subtitle, 14, y);
    y += 5;
  }
  doc.text(`Generated ${new Date().toLocaleString()}`, 14, y);
  y += 5;
  for (const [k, v] of options.meta ?? []) {
    doc.text(`${k}: ${v}`, 14, y);
    y += 5;
  }
  doc.setTextColor(0);

  autoTable(doc, {
    head: [columns.map((c) => c.header)],
    body: rows.map((r) => columns.map((c) => String(c.accessor(r) ?? ""))),
    startY: y + 2,
    styles: { fontSize: 8, cellPadding: 2 },
    headStyles: { fillColor: [30, 41, 59] },
    margin: { left: 14, right: 14 },
  });

  doc.save(ensureExt(filename, "pdf"));
}

function ensureExt(name: string, ext: string): string {
  return name.toLowerCase().endsWith(`.${ext}`) ? name : `${name}.${ext}`;
}

export type ExportFormat = "csv" | "xlsx" | "pdf" | "json";

/** One-call dispatcher used by the ExportMenu. */
export async function exportAs<T>(
  format: ExportFormat,
  opts: {
    filename: string;
    title: string;
    columns: Column<T>[];
    rows: T[];
    json?: unknown;
    pdf?: PdfOptions;
  },
): Promise<void> {
  switch (format) {
    case "json":
      return exportJSON(opts.filename, opts.json ?? opts.rows);
    case "csv":
      return exportCSV(opts.filename, opts.columns, opts.rows);
    case "xlsx":
      return exportExcel(opts.filename, opts.columns, opts.rows);
    case "pdf":
      return exportPDF(opts.filename, opts.title, opts.columns, opts.rows, opts.pdf);
  }
}
