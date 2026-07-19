"use client";

/**
 * Applies user preferences (Phase 6, WS1/WS7) to the document: density
 * drives global spacing, reduce-motion disables transitions. Rendering
 * nothing, it only syncs the persisted preferences to DOM attributes that
 * globals.css keys off. Also respects the OS prefers-reduced-motion.
 */
import { useEffect } from "react";
import { useUxStore } from "@/stores/ux-store";

export function UxEffects() {
  const density = useUxStore((s) => s.preferences.density);
  const reduceMotion = useUxStore((s) => s.preferences.reduceMotion);
  const highContrast = useUxStore((s) => s.preferences.highContrast);

  useEffect(() => {
    document.documentElement.setAttribute("data-density", density);
  }, [density]);

  useEffect(() => {
    const os = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;
    document.documentElement.classList.toggle("reduce-motion", reduceMotion || os);
  }, [reduceMotion]);

  useEffect(() => {
    document.documentElement.classList.toggle("high-contrast", !!highContrast);
  }, [highContrast]);

  return null;
}
