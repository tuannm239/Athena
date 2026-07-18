"use client";

import { usePathname } from "next/navigation";
import { useMemo, useState } from "react";
import { Navbar } from "./navbar";
import { Sidebar } from "./sidebar";
import { CommandPalette } from "@/components/command-palette";
import { KeyboardHelp } from "@/components/keyboard-help";
import { UxEffects } from "@/components/ux-effects";
import { useCommandStore } from "@/stores/command-store";
import { useHotkeys, type Hotkey } from "@/hooks/use-hotkeys";
import { useNotificationSync } from "@/hooks/use-notification-sync";
import { cn } from "@/lib/utils";

const NO_SHELL = ["/login"];

/** Runs notification derivation only inside the authenticated shell. */
function NotificationSync() {
  useNotificationSync();
  return null;
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);
  const toggleCommand = useCommandStore((s) => s.toggle);
  const setHelpOpen = useCommandStore((s) => s.setHelpOpen);

  const hotkeys = useMemo<Hotkey[]>(
    () => [
      { key: "k", meta: true, allowInInput: true, handler: () => toggleCommand() },
      { key: "?", handler: () => setHelpOpen(true) },
    ],
    [toggleCommand, setHelpOpen],
  );
  useHotkeys(hotkeys);

  if (NO_SHELL.includes(pathname)) return <>{children}</>;

  return (
    <div className="flex h-screen flex-col">
      <Navbar onToggleSidebar={() => setMobileOpen((v) => !v)} />
      <div className="flex flex-1 overflow-hidden">
        {/* desktop sidebar */}
        <aside className="hidden w-60 shrink-0 border-r bg-card lg:block">
          <Sidebar />
        </aside>

        {/* mobile drawer */}
        {mobileOpen ? (
          <div className="fixed inset-0 z-40 lg:hidden">
            <div
              className="absolute inset-0 bg-black/50"
              onClick={() => setMobileOpen(false)}
              aria-hidden
            />
            <aside className="absolute left-0 top-0 h-full w-64 border-r bg-card">
              <Sidebar onNavigate={() => setMobileOpen(false)} />
            </aside>
          </div>
        ) : null}

        <main className={cn("flex-1 overflow-y-auto")}>
          <div className="mx-auto max-w-[1600px] p-4 md:p-6">{children}</div>
        </main>
      </div>
      <CommandPalette />
      <KeyboardHelp />
      <NotificationSync />
      <UxEffects />
    </div>
  );
}
