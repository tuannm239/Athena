"use client";

/**
 * Client-side UX state (Phase 6, WS7): favorites, recent items, pinned
 * companies, saved filters, and user preferences. Persisted to
 * localStorage so it survives reloads. This is presentation state only —
 * it holds no business logic and never affects decisions (the backend
 * remains the single source of truth).
 */
import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";

export type EntityType =
  | "decision"
  | "company"
  | "portfolio"
  | "report"
  | "page"
  | "evidence"
  | "knowledge-graph";

export interface RecentItem {
  type: EntityType;
  id: string;
  label: string;
  href: string;
  at: number;
}

export type FavoriteItem = Omit<RecentItem, "at">;

export interface SavedFilter {
  id: string;
  name: string;
  /** URL query string (without the leading '?') that reproduces the view. */
  query: string;
}

export type Density = "comfortable" | "compact";

export type Language = "en" | "vi";

export interface Preferences {
  density: Density;
  /** Landing route after login. */
  landingPage: string;
  /** Show clearly-labelled sample data when a backend endpoint is 501. */
  showSampleData: boolean;
  /** Reduce non-essential motion. */
  reduceMotion: boolean;
  /** UI language preference (interface copy). */
  language: Language;
  /** Higher-contrast palette for accessibility. */
  highContrast: boolean;
}

const DEFAULT_PREFERENCES: Preferences = {
  density: "comfortable",
  landingPage: "/",
  showSampleData: true,
  reduceMotion: false,
  language: "en",
  highContrast: false,
};

const MAX_RECENT = 20;

interface UxState {
  favorites: FavoriteItem[];
  recent: RecentItem[];
  pinnedCompanies: string[];
  savedFilters: Record<string, SavedFilter[]>;
  preferences: Preferences;

  isFavorite: (type: EntityType, id: string) => boolean;
  toggleFavorite: (item: FavoriteItem) => void;
  pushRecent: (item: Omit<RecentItem, "at">) => void;
  clearRecent: () => void;

  isPinned: (ticker: string) => boolean;
  togglePin: (ticker: string) => void;

  saveFilter: (page: string, name: string, query: string) => void;
  removeFilter: (page: string, id: string) => void;

  setPreferences: (patch: Partial<Preferences>) => void;
  reset: () => void;
}

export const useUxStore = create<UxState>()(
  persist(
    (set, get) => ({
      favorites: [],
      recent: [],
      pinnedCompanies: [],
      savedFilters: {},
      preferences: DEFAULT_PREFERENCES,

      isFavorite: (type, id) => get().favorites.some((f) => f.type === type && f.id === id),

      toggleFavorite: (item) =>
        set((s) => {
          const exists = s.favorites.some((f) => f.type === item.type && f.id === item.id);
          return {
            favorites: exists
              ? s.favorites.filter((f) => !(f.type === item.type && f.id === item.id))
              : [item, ...s.favorites].slice(0, 100),
          };
        }),

      pushRecent: (item) =>
        set((s) => {
          const deduped = s.recent.filter((r) => !(r.type === item.type && r.id === item.id));
          return { recent: [{ ...item, at: Date.now() }, ...deduped].slice(0, MAX_RECENT) };
        }),

      clearRecent: () => set({ recent: [] }),

      isPinned: (ticker) => get().pinnedCompanies.includes(ticker.toUpperCase()),

      togglePin: (ticker) =>
        set((s) => {
          const t = ticker.toUpperCase();
          return {
            pinnedCompanies: s.pinnedCompanies.includes(t)
              ? s.pinnedCompanies.filter((x) => x !== t)
              : [t, ...s.pinnedCompanies].slice(0, 50),
          };
        }),

      saveFilter: (page, name, query) =>
        set((s) => {
          const id = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
          const list = s.savedFilters[page] ?? [];
          return { savedFilters: { ...s.savedFilters, [page]: [...list, { id, name, query }] } };
        }),

      removeFilter: (page, id) =>
        set((s) => ({
          savedFilters: {
            ...s.savedFilters,
            [page]: (s.savedFilters[page] ?? []).filter((f) => f.id !== id),
          },
        })),

      setPreferences: (patch) => set((s) => ({ preferences: { ...s.preferences, ...patch } })),

      reset: () =>
        set({
          favorites: [],
          recent: [],
          pinnedCompanies: [],
          savedFilters: {},
          preferences: DEFAULT_PREFERENCES,
        }),
    }),
    {
      name: "athena-ux",
      version: 2,
      migrate: (persisted, version) => {
        const s = persisted as UxState;
        if (version < 2 && s?.preferences) {
          s.preferences = { ...DEFAULT_PREFERENCES, ...s.preferences };
        }
        return s;
      },
      storage: createJSONStorage(() => {
        if (typeof window === "undefined") {
          return { getItem: () => null, setItem: () => {}, removeItem: () => {} };
        }
        return window.localStorage;
      }),
    },
  ),
);
