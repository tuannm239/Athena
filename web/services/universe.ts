/**
 * Investment universe management service. Reads/edits the editable
 * `watchlist_universe` the sync layer covers. All calls go through the backend
 * REST API — the frontend never talks to vnstock or the database directly.
 */
import { apiRequest } from "@/lib/api-client";

export type SyncLevel = "REALTIME" | "HIGH" | "NORMAL" | "LOW";
export const SYNC_LEVELS: SyncLevel[] = ["REALTIME", "HIGH", "NORMAL", "LOW"];

export interface UniverseEntry {
  symbol: string;
  sector: string;
  sync_level: SyncLevel;
  priority: number;
  is_active: boolean;
}

export interface UniverseUpsert {
  symbol: string;
  sector?: string;
  sync_level?: SyncLevel;
  is_active?: boolean;
}

export const universeService = {
  list: () => apiRequest<UniverseEntry[]>("/universe"),
  upsert: (body: UniverseUpsert) =>
    apiRequest<UniverseEntry>("/universe", { method: "POST", body }),
  patch: (symbol: string, body: Partial<Pick<UniverseEntry, "sync_level" | "is_active">>) =>
    apiRequest<UniverseEntry>(`/universe/${symbol}`, { method: "PATCH", body }),
  remove: (symbol: string) =>
    apiRequest<{ removed: boolean }>(`/universe/${symbol}`, { method: "DELETE" }),
};
