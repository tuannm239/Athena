"use client";

import { useEffect } from "react";

/** True when focus is in a text input / textarea / contenteditable. */
export function isTypingTarget(el: EventTarget | null): boolean {
  if (!(el instanceof HTMLElement)) return false;
  const tag = el.tagName.toLowerCase();
  return tag === "input" || tag === "textarea" || tag === "select" || el.isContentEditable;
}

export interface Hotkey {
  /** Lowercase key, e.g. "k", "/", "?". */
  key: string;
  meta?: boolean; // Cmd (mac) or Ctrl (win/linux) — matched against either
  shift?: boolean;
  /** Fire even while typing in an input (default false). */
  allowInInput?: boolean;
  handler: (e: KeyboardEvent) => void;
}

/**
 * Register global keyboard shortcuts (Phase 6, WS4/WS7). Cleans up on
 * unmount. `meta` matches Cmd OR Ctrl so shortcuts work cross-platform.
 */
export function useHotkeys(hotkeys: Hotkey[]): void {
  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      for (const hk of hotkeys) {
        if (e.key.toLowerCase() !== hk.key.toLowerCase()) continue;
        if (hk.meta && !(e.metaKey || e.ctrlKey)) continue;
        if (!hk.meta && (e.metaKey || e.ctrlKey)) continue;
        if (hk.shift && !e.shiftKey) continue;
        if (!hk.allowInInput && isTypingTarget(e.target)) continue;
        e.preventDefault();
        hk.handler(e);
        return;
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [hotkeys]);
}
