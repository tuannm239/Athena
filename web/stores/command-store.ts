"use client";

import { create } from "zustand";

interface CommandState {
  open: boolean;
  setOpen: (open: boolean) => void;
  toggle: () => void;
}

/** Global open-state for the Command Palette (Phase 6, WS4/WS7). */
export const useCommandStore = create<CommandState>((set, get) => ({
  open: false,
  setOpen: (open) => set({ open }),
  toggle: () => set({ open: !get().open }),
}));
