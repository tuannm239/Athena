/**
 * Global-search helpers (Phase 6, WS4). Pure functions + a static command
 * index; live data results (decisions, companies, portfolios) are merged in
 * by the command palette using React Query. Search is client-side over the
 * loaded set plus direct lookups — no new backend endpoints, fully
 * compatible with the existing API.
 */
import type { LucideIcon } from "lucide-react";
import {
  Building2,
  FileText,
  LayoutDashboard,
  Network,
  Briefcase,
  Target,
  Sparkles,
} from "lucide-react";
import { NAV_SECTIONS } from "./navigation";
import type { EntityType } from "@/stores/ux-store";

export interface SearchResult {
  type: EntityType | "action";
  id: string;
  label: string;
  sublabel?: string;
  href?: string;
  onSelect?: () => void;
  icon?: LucideIcon;
  group: string;
}

export function normalize(q: string): string {
  return q.trim().toLowerCase();
}

/** Lightweight subsequence + substring score; higher is better, 0 = no match. */
export function score(query: string, text: string): number {
  const q = normalize(query);
  const t = text.toLowerCase();
  if (!q) return 1;
  if (t === q) return 100;
  if (t.startsWith(q)) return 80;
  const idx = t.indexOf(q);
  if (idx >= 0) return 60 - Math.min(idx, 40);
  // subsequence fallback
  let qi = 0;
  for (let i = 0; i < t.length && qi < q.length; i++) if (t[i] === q[qi]) qi++;
  return qi === q.length ? 20 : 0;
}

/** Navigable pages from the sidebar, as search/command entries. */
export function navResults(query: string): SearchResult[] {
  const items = NAV_SECTIONS.flatMap((s) =>
    s.items.map((it) => ({
      type: "page" as const,
      id: it.href,
      label: it.label,
      sublabel: s.title,
      href: it.href,
      icon: it.icon,
      group: "Pages",
    })),
  );
  return rank(query, items, (r) => r.label);
}

/** The report catalogue (Phase 6, WS3) as navigable entries. */
export const REPORT_KINDS = [
  "Decision",
  "Portfolio",
  "Risk",
  "Backtest",
  "Scenario",
  "Daily",
  "Weekly",
  "Monthly",
] as const;

export function reportResults(query: string): SearchResult[] {
  const items = REPORT_KINDS.map((k) => ({
    type: "report" as const,
    id: `report-${k.toLowerCase()}`,
    label: `${k} Report`,
    sublabel: "Generate PDF / Excel",
    href: `/reports?kind=${k.toLowerCase()}`,
    icon: FileText,
    group: "Reports",
  }));
  return rank(query, items, (r) => r.label);
}

/** Quick actions available from the palette. */
export function actionResults(query: string, actions: SearchResult[]): SearchResult[] {
  return rank(query, actions, (r) => r.label);
}

export function rank<T extends { }>(
  query: string,
  items: T[],
  key: (t: T) => string,
): (T & { _score: number })[] {
  return items
    .map((it) => ({ ...it, _score: score(query, key(it)) }))
    .filter((it) => it._score > 0)
    .sort((a, b) => b._score - a._score);
}

export const SEARCH_ICONS: Record<string, LucideIcon> = {
  decision: Target,
  company: Building2,
  portfolio: Briefcase,
  report: FileText,
  page: LayoutDashboard,
  "knowledge-graph": Network,
  evidence: Sparkles,
};
