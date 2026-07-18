"use client";

import { create } from "zustand";

interface CommandState {
  open: boolean;
  setOpen: (open: boolean) => void;
  toggle: () => void;
  helpOpen: boolean;
  setHelpOpen: (open: boolean) => void;
}

/** Global open-state for the Command Palette + keyboard-help (Phase 6). */
export const useCommandStore = create<CommandState>((set, get) => ({
  open: false,
  setOpen: (open) => set({ open }),
  toggle: () => set({ open: !get().open }),
  helpOpen: false,
  setHelpOpen: (helpOpen) => set({ helpOpen }),
}));
