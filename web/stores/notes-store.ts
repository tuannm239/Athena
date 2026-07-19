"use client";

/**
 * Research notes & attachments (Phase 8). Client-side, persisted to
 * localStorage: a note can carry attached files (stored as small data URLs),
 * link to a company and/or a decision, be marked human-reviewed, and it keeps
 * an append-only audit trail. This is presentation/workspace state — the
 * backend remains the system of record for decisions and evidence.
 */
import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";

export interface Attachment {
  id: string;
  name: string;
  kind: string; // mime type or extension
  size: number;
  /** data: URL — only small files are stored inline; larger ones keep metadata only. */
  dataUrl?: string;
}

export interface AuditEntry {
  at: number;
  action: string;
}

export interface Note {
  id: string;
  title: string;
  body: string;
  ticker?: string;
  decisionId?: string;
  attachments: Attachment[];
  reviewed: boolean;
  createdAt: number;
  updatedAt: number;
  audit: AuditEntry[];
}

const MAX_INLINE_BYTES = 512 * 1024; // 512 KB inline cap per attachment

interface NotesState {
  notes: Note[];
  add: (note: Pick<Note, "title" | "body"> & Partial<Note>) => string;
  update: (id: string, patch: Partial<Note>) => void;
  remove: (id: string) => void;
  toggleReviewed: (id: string) => void;
  addAttachment: (id: string, att: Attachment) => void;
}

function uid(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

export const useNotesStore = create<NotesState>()(
  persist(
    (set) => ({
      notes: [],

      add: (note) => {
        const id = note.id ?? uid();
        const now = Date.now();
        set((s) => ({
          notes: [
            {
              id,
              title: note.title,
              body: note.body,
              ticker: note.ticker,
              decisionId: note.decisionId,
              attachments: note.attachments ?? [],
              reviewed: note.reviewed ?? false,
              createdAt: now,
              updatedAt: now,
              audit: [{ at: now, action: "created" }],
            },
            ...s.notes,
          ],
        }));
        return id;
      },

      update: (id, patch) =>
        set((s) => ({
          notes: s.notes.map((n) =>
            n.id === id
              ? {
                  ...n,
                  ...patch,
                  updatedAt: Date.now(),
                  audit: [...n.audit, { at: Date.now(), action: "edited" }],
                }
              : n,
          ),
        })),

      remove: (id) => set((s) => ({ notes: s.notes.filter((n) => n.id !== id) })),

      toggleReviewed: (id) =>
        set((s) => ({
          notes: s.notes.map((n) =>
            n.id === id
              ? {
                  ...n,
                  reviewed: !n.reviewed,
                  updatedAt: Date.now(),
                  audit: [
                    ...n.audit,
                    { at: Date.now(), action: n.reviewed ? "review cleared" : "reviewed" },
                  ],
                }
              : n,
          ),
        })),

      addAttachment: (id, att) =>
        set((s) => ({
          notes: s.notes.map((n) =>
            n.id === id
              ? {
                  ...n,
                  attachments: [...n.attachments, att],
                  updatedAt: Date.now(),
                  audit: [...n.audit, { at: Date.now(), action: `attached ${att.name}` }],
                }
              : n,
          ),
        })),
    }),
    {
      name: "athena-notes",
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

export { MAX_INLINE_BYTES, uid as newId };
