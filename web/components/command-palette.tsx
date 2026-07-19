"use client";

/**
 * Command Palette + global search (Phase 6, WS4/WS7).
 *
 * Opens on Cmd/Ctrl+K (or the navbar search button). Searches across pages,
 * reports, recent items, favorites, decisions, companies and portfolios —
 * all client-side over already-loaded data plus direct lookups, so it adds
 * no backend endpoints and stays fully API-compatible. Fully keyboard
 * driven (↑/↓ to move, ↵ to open, Esc to close) and accessible.
 */
import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Clock, CornerDownLeft, Search, Star, X } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { decisionsService } from "@/services/decisions";
import { companiesService } from "@/services/market";
import { useCommandStore } from "@/stores/command-store";
import { useUxStore } from "@/stores/ux-store";
import {
  navResults,
  reportResults,
  rank,
  SEARCH_ICONS,
  type SearchResult,
} from "@/lib/search";
import { cn } from "@/lib/utils";

const TICKER_RE = /^[A-Za-z]{2,6}$/;

/** Gate: mount the heavy palette (router + data queries) only when open. */
export function CommandPalette() {
  const open = useCommandStore((s) => s.open);
  if (!open) return null;
  return <CommandPaletteInner />;
}

function CommandPaletteInner() {
  const setOpen = useCommandStore((s) => s.setOpen);
  const router = useRouter();
  const open = true;

  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  const favorites = useUxStore((s) => s.favorites);
  const recent = useUxStore((s) => s.recent);
  const pushRecent = useUxStore((s) => s.pushRecent);

  // Decisions: fetch a page once the palette is open; filter client-side.
  const decisions = useQuery({
    queryKey: ["palette-decisions"],
    queryFn: () => decisionsService.list({ limit: 50 }),
    enabled: open,
    staleTime: 30_000,
  });

  // Direct company lookup when the query looks like a ticker.
  const companyLookup = useQuery({
    queryKey: ["palette-company", query.toUpperCase()],
    queryFn: () => companiesService.get(query.toUpperCase()),
    enabled: open && TICKER_RE.test(query.trim()),
    staleTime: 30_000,
  });

  useEffect(() => {
    if (open) {
      setQuery("");
      setActive(0);
      // focus after paint
      const t = setTimeout(() => inputRef.current?.focus(), 10);
      return () => clearTimeout(t);
    }
  }, [open]);

  const results = useMemo<SearchResult[]>(() => {
    const q = query.trim();
    const groups: SearchResult[] = [];

    if (!q) {
      // Default view: recent + favorites + top pages.
      for (const r of recent.slice(0, 6)) {
        groups.push({ ...r, group: "Recent", icon: SEARCH_ICONS[r.type] });
      }
      for (const f of favorites.slice(0, 6)) {
        groups.push({ ...f, group: "Favorites", icon: SEARCH_ICONS[f.type] });
      }
      groups.push(...navResults("").slice(0, 8));
      return groups;
    }

    // decisions
    const dItems = (decisions.data?.items ?? []).map((d) => ({
      type: "decision" as const,
      id: d.id,
      label: d.hypothesis,
      sublabel: `Decision · ${d.status}`,
      href: `/decisions/${d.id}`,
      icon: SEARCH_ICONS.decision,
      group: "Decisions",
    }));
    groups.push(...rank(q, dItems, (r) => `${r.label} ${r.id}`).slice(0, 6));

    // company (direct ticker lookup)
    if (companyLookup.data) {
      const c = companyLookup.data.data;
      groups.push({
        type: "company",
        id: c.ticker,
        label: `${c.ticker} — ${c.name}`,
        sublabel: `${c.exchange} · ${c.sector}`,
        href: `/companies/${c.ticker}`,
        icon: SEARCH_ICONS.company,
        group: "Companies",
      });
    }

    groups.push(...navResults(q).slice(0, 6));
    groups.push(...reportResults(q).slice(0, 6));

    // fallback action: search companies page
    groups.push({
      type: "action",
      id: "search-companies",
      label: `Search companies for “${q}”`,
      href: `/companies?q=${encodeURIComponent(q)}`,
      icon: Search,
      group: "Actions",
    });

    return groups;
  }, [query, recent, favorites, decisions.data, companyLookup.data]);

  useEffect(() => {
    setActive((a) => Math.min(a, Math.max(results.length - 1, 0)));
  }, [results.length]);

  function choose(r: SearchResult | undefined) {
    if (!r) return;
    if (r.href) {
      if (r.type !== "action" && r.type !== "page") {
        pushRecent({ type: r.type, id: r.id, label: r.label, href: r.href });
      }
      router.push(r.href);
    }
    r.onSelect?.();
    setOpen(false);
  }

  function onKeyDown(e: React.KeyboardEvent) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive((a) => Math.min(a + 1, results.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((a) => Math.max(a - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      choose(results[active]);
    } else if (e.key === "Escape") {
      e.preventDefault();
      setOpen(false);
    }
  }

  // keep the active row scrolled into view
  useEffect(() => {
    const node = listRef.current?.querySelector<HTMLElement>(`[data-idx="${active}"]`);
    node?.scrollIntoView({ block: "nearest" });
  }, [active]);

  if (!open) return null;

  // group results in stable order for rendering
  const grouped: [string, SearchResult[]][] = [];
  for (const r of results) {
    const last = grouped[grouped.length - 1];
    if (last && last[0] === r.group) last[1].push(r);
    else grouped.push([r.group, [r]]);
  }
  let idx = -1;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center p-4 pt-[12vh]"
      role="dialog"
      aria-modal="true"
      aria-label="Command palette"
    >
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={() => setOpen(false)} />
      <div className="relative z-10 w-full max-w-xl overflow-hidden rounded-xl border bg-card shadow-2xl">
        <div className="flex items-center gap-2 border-b px-3">
          <Search className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden />
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder="Search decisions, companies, reports, pages…"
            className="h-12 w-full bg-transparent text-sm outline-none placeholder:text-muted-foreground"
            aria-label="Search"
            autoComplete="off"
            spellCheck={false}
          />
          <button
            onClick={() => setOpen(false)}
            className="rounded p-1 text-muted-foreground hover:bg-accent"
            aria-label="Close"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div ref={listRef} className="max-h-[50vh] overflow-y-auto p-2">
          {results.length === 0 ? (
            <p className="px-3 py-6 text-center text-sm text-muted-foreground">
              No results for “{query}”.
            </p>
          ) : (
            grouped.map(([group, items]) => (
              <div key={group} className="mb-1">
                <p className="px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
                  {group}
                </p>
                {items.map((r) => {
                  idx += 1;
                  const i = idx;
                  const Icon = r.icon;
                  return (
                    <button
                      key={`${r.type}-${r.id}`}
                      data-idx={i}
                      onClick={() => choose(r)}
                      onMouseEnter={() => setActive(i)}
                      className={cn(
                        "flex w-full items-center gap-3 rounded-md px-2 py-2 text-left text-sm",
                        i === active ? "bg-accent text-accent-foreground" : "hover:bg-accent/50",
                      )}
                    >
                      {group === "Recent" ? (
                        <Clock className="h-4 w-4 shrink-0 text-muted-foreground" />
                      ) : group === "Favorites" ? (
                        <Star className="h-4 w-4 shrink-0 text-warn" />
                      ) : Icon ? (
                        <Icon className="h-4 w-4 shrink-0 text-muted-foreground" />
                      ) : null}
                      <span className="min-w-0 flex-1 truncate">{r.label}</span>
                      {r.sublabel ? (
                        <span className="shrink-0 text-xs text-muted-foreground">{r.sublabel}</span>
                      ) : null}
                      {i === active ? (
                        <CornerDownLeft className="h-3 w-3 shrink-0 text-muted-foreground" />
                      ) : null}
                    </button>
                  );
                })}
              </div>
            ))
          )}
        </div>

        <div className="flex items-center justify-between border-t px-3 py-2 text-[10px] text-muted-foreground">
          <span>↑↓ navigate · ↵ open · esc close</span>
          <span>Athena · decision support</span>
        </div>
      </div>
    </div>
  );
}
