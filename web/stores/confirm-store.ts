"use client";

/** Imperative confirmation dialog (Athena V1): `await confirm({...})`. */
import { create } from "zustand";

export interface ConfirmOptions {
  title: string;
  description?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  destructive?: boolean;
}

interface PendingConfirm extends ConfirmOptions {
  resolve: (ok: boolean) => void;
}

interface ConfirmState {
  pending: PendingConfirm | null;
  request: (options: ConfirmOptions) => Promise<boolean>;
  settle: (ok: boolean) => void;
}

export const useConfirmStore = create<ConfirmState>((set, get) => ({
  pending: null,
  request: (options) =>
    new Promise<boolean>((resolve) => {
      set({ pending: { ...options, resolve } });
    }),
  settle: (ok) => {
    const p = get().pending;
    if (p) p.resolve(ok);
    set({ pending: null });
  },
}));

export function confirm(options: ConfirmOptions): Promise<boolean> {
  return useConfirmStore.getState().request(options);
}
