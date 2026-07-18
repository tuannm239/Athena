"use client";

/**
 * In-app notifications (Phase 6, WS5). No email/SMS — purely in-app.
 * Notifications are derived from real signals the app already fetches
 * (pending reviews, component health) by useNotificationSync and upserted
 * here by a stable key so they never duplicate. Read/dismissed state is
 * persisted so a dismissed alert stays dismissed across reloads.
 */
import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";

export type NotificationKind = "review" | "pipeline" | "provider" | "system";
export type Severity = "info" | "warn" | "error";

export interface NotificationItem {
  /** Stable key — re-upserting the same key updates in place, never dupes. */
  id: string;
  kind: NotificationKind;
  severity: Severity;
  title: string;
  body: string;
  href?: string;
  at: number;
  read: boolean;
}

export type NotificationInput = Omit<NotificationItem, "at" | "read">;

interface NotificationState {
  items: NotificationItem[];
  dismissed: string[];
  upsert: (input: NotificationInput) => void;
  /** Reconcile a full set for a category: upsert present, auto-clear absent. */
  reconcile: (kind: NotificationKind, inputs: NotificationInput[]) => void;
  markRead: (id: string) => void;
  markAllRead: () => void;
  dismiss: (id: string) => void;
  clearAll: () => void;
  unreadCount: () => number;
}

const MAX = 50;

export const useNotificationStore = create<NotificationState>()(
  persist(
    (set, get) => ({
      items: [],
      dismissed: [],

      upsert: (input) =>
        set((s) => {
          if (s.dismissed.includes(input.id)) return s;
          const existing = s.items.find((n) => n.id === input.id);
          if (existing) {
            return {
              items: s.items.map((n) =>
                n.id === input.id ? { ...n, ...input, at: n.at, read: n.read } : n,
              ),
            };
          }
          return {
            items: [{ ...input, at: Date.now(), read: false }, ...s.items].slice(0, MAX),
          };
        }),

      reconcile: (kind, inputs) =>
        set((s) => {
          const keep = new Set(inputs.map((i) => i.id));
          // drop stale items of this kind whose condition no longer holds
          let items = s.items.filter((n) => n.kind !== kind || keep.has(n.id));
          for (const input of inputs) {
            if (s.dismissed.includes(input.id)) continue;
            const existing = items.find((n) => n.id === input.id);
            if (existing) {
              items = items.map((n) =>
                n.id === input.id ? { ...n, ...input, at: n.at, read: n.read } : n,
              );
            } else {
              items = [{ ...input, at: Date.now(), read: false }, ...items];
            }
          }
          return { items: items.slice(0, MAX) };
        }),

      markRead: (id) =>
        set((s) => ({ items: s.items.map((n) => (n.id === id ? { ...n, read: true } : n)) })),

      markAllRead: () => set((s) => ({ items: s.items.map((n) => ({ ...n, read: true })) })),

      dismiss: (id) =>
        set((s) => ({
          items: s.items.filter((n) => n.id !== id),
          dismissed: [...s.dismissed, id].slice(-200),
        })),

      clearAll: () => set((s) => ({ items: [], dismissed: s.dismissed })),

      unreadCount: () => get().items.filter((n) => !n.read).length,
    }),
    {
      name: "athena-notifications",
      version: 1,
      storage: createJSONStorage(() => {
        if (typeof window === "undefined") {
          return { getItem: () => null, setItem: () => {}, removeItem: () => {} };
        }
        return window.localStorage;
      }),
    },
  ),
);
