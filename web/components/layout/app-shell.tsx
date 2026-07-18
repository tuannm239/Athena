"use client";

import { usePathname } from "next/navigation";
import { useState } from "react";
import { Navbar } from "./navbar";
import { Sidebar } from "./sidebar";
import { cn } from "@/lib/utils";

const NO_SHELL = ["/login"];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

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
    </div>
  );
}
