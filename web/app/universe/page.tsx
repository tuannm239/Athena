"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Boxes, Plus, RefreshCw, Trash2 } from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Spinner } from "@/components/ui/spinner";
import {
  SYNC_LEVELS,
  universeService,
  type SyncLevel,
  type UniverseEntry,
} from "@/services/universe";

const LEVEL_TONE: Record<SyncLevel, string> = {
  REALTIME: "bg-emerald-500/15 text-emerald-500",
  HIGH: "bg-sky-500/15 text-sky-500",
  NORMAL: "bg-muted text-muted-foreground",
  LOW: "bg-amber-500/15 text-amber-500",
};

export default function UniversePage() {
  const [entries, setEntries] = useState<UniverseEntry[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [symbol, setSymbol] = useState("");
  const [sector, setSector] = useState("");
  const [level, setLevel] = useState<SyncLevel>("NORMAL");

  const load = useCallback(async () => {
    try {
      setError(null);
      setEntries(await universeService.list());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load universe");
      setEntries([]);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const run = useCallback(
    async (fn: () => Promise<unknown>) => {
      setBusy(true);
      try {
        await fn();
        await load();
      } catch (e) {
        setError(e instanceof Error ? e.message : "Action failed");
      } finally {
        setBusy(false);
      }
    },
    [load],
  );

  const add = () => {
    const s = symbol.trim().toUpperCase();
    if (!s) return;
    void run(async () => {
      await universeService.upsert({ symbol: s, sector: sector.trim() || "OTHER", sync_level: level });
      setSymbol("");
      setSector("");
    });
  };

  const grouped = useMemo(() => {
    const by: Record<string, UniverseEntry[]> = {};
    for (const e of entries ?? []) (by[e.sector] ??= []).push(e);
    return Object.entries(by).sort(([a], [b]) => a.localeCompare(b));
  }, [entries]);

  const activeCount = (entries ?? []).filter((e) => e.is_active).length;

  return (
    <>
      <PageHeader
        title="Investment Universe"
        description="The editable set of symbols the platform synchronises. Edits here change what `athena sync universe` covers — no code change needed."
      />

      <Card className="mb-4">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Plus className="h-4 w-4" /> Add / update a symbol
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap items-end gap-3">
            <label className="flex flex-col gap-1 text-xs text-muted-foreground">
              Symbol
              <input
                value={symbol}
                onChange={(e) => setSymbol(e.target.value)}
                placeholder="FPT"
                className="w-28 rounded-md border bg-background px-2 py-1.5 text-sm uppercase"
              />
            </label>
            <label className="flex flex-col gap-1 text-xs text-muted-foreground">
              Sector
              <input
                value={sector}
                onChange={(e) => setSector(e.target.value)}
                placeholder="BANKING"
                className="w-40 rounded-md border bg-background px-2 py-1.5 text-sm uppercase"
              />
            </label>
            <label className="flex flex-col gap-1 text-xs text-muted-foreground">
              Sync level
              <select
                value={level}
                onChange={(e) => setLevel(e.target.value as SyncLevel)}
                className="rounded-md border bg-background px-2 py-1.5 text-sm"
              >
                {SYNC_LEVELS.map((l) => (
                  <option key={l} value={l}>
                    {l}
                  </option>
                ))}
              </select>
            </label>
            <Button onClick={add} disabled={busy || !symbol.trim()}>
              Add
            </Button>
            <Button variant="ghost" onClick={() => void load()} disabled={busy}>
              <RefreshCw className="mr-1 h-4 w-4" /> Refresh
            </Button>
          </div>
          {error && <p className="mt-2 text-sm text-destructive">{error}</p>}
        </CardContent>
      </Card>

      {entries === null ? (
        <div className="flex justify-center py-16">
          <Spinner />
        </div>
      ) : entries.length === 0 ? (
        <EmptyState
          icon={Boxes}
          title="Universe is empty"
          description="Add symbols above, or let the boot seed populate the default universe."
        />
      ) : (
        <div className="space-y-4">
          <p className="text-sm text-muted-foreground">
            {entries.length} symbols · {activeCount} active
          </p>
          {grouped.map(([sec, items]) => (
            <Card key={sec}>
              <CardHeader>
                <CardTitle className="text-sm text-muted-foreground">
                  {sec} ({items.length})
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="divide-y">
                  {items.map((e) => (
                    <li key={e.symbol} className="flex items-center gap-3 py-2">
                      <span className="w-16 font-semibold">{e.symbol}</span>
                      <select
                        value={e.sync_level}
                        disabled={busy}
                        onChange={(ev) =>
                          void run(() =>
                            universeService.patch(e.symbol, {
                              sync_level: ev.target.value as SyncLevel,
                            }),
                          )
                        }
                        className={`rounded px-2 py-0.5 text-xs ${LEVEL_TONE[e.sync_level]}`}
                      >
                        {SYNC_LEVELS.map((l) => (
                          <option key={l} value={l}>
                            {l}
                          </option>
                        ))}
                      </select>
                      <button
                        type="button"
                        disabled={busy}
                        onClick={() =>
                          void run(() =>
                            universeService.patch(e.symbol, { is_active: !e.is_active }),
                          )
                        }
                        className="ml-auto"
                        aria-label={e.is_active ? "Deactivate" : "Activate"}
                      >
                        <Badge variant={e.is_active ? "gain" : "muted"}>
                          {e.is_active ? "active" : "inactive"}
                        </Badge>
                      </button>
                      <button
                        type="button"
                        disabled={busy}
                        onClick={() => void run(() => universeService.remove(e.symbol))}
                        aria-label="Remove"
                        className="text-muted-foreground hover:text-destructive"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </>
  );
}
