"use client";

import { LogOut, Menu, Moon, Search, Sun } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useTheme } from "@/providers/theme-provider";
import { useAuthStore } from "@/stores/auth-store";
import { useCommandStore } from "@/stores/command-store";
import { NotificationBell } from "@/components/notification-bell";

export function Navbar({ onToggleSidebar }: { onToggleSidebar: () => void }) {
  const { theme, toggle } = useTheme();
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const openCommand = useCommandStore((s) => s.setOpen);

  return (
    <header className="flex h-14 shrink-0 items-center gap-3 border-b bg-card px-4">
      <Button
        variant="ghost"
        size="icon"
        className="lg:hidden"
        onClick={onToggleSidebar}
        aria-label="Toggle navigation"
      >
        <Menu className="h-5 w-5" />
      </Button>
      <div className="flex items-center gap-2">
        <div className="flex h-7 w-7 items-center justify-center rounded bg-primary text-primary-foreground font-bold">
          A
        </div>
        <span className="font-semibold tracking-tight">ATHENA</span>
        <span className="hidden text-xs text-muted-foreground sm:inline">
          Financial Decision Intelligence
        </span>
      </div>

      {/* Global search trigger (Cmd/Ctrl+K) */}
      <button
        onClick={() => openCommand(true)}
        className="ml-auto hidden items-center gap-2 rounded-md border bg-background px-3 py-1.5 text-xs text-muted-foreground transition-colors hover:bg-accent sm:flex"
        aria-label="Search (Command+K)"
      >
        <Search className="h-3.5 w-3.5" />
        <span>Search…</span>
        <kbd className="rounded border bg-muted px-1.5 py-0.5 font-mono text-[10px]">⌘K</kbd>
      </button>

      <div className="ml-auto flex items-center gap-2 sm:ml-2">
        <Button
          variant="ghost"
          size="icon"
          className="sm:hidden"
          onClick={() => openCommand(true)}
          aria-label="Search"
        >
          <Search className="h-4 w-4" />
        </Button>
        {user ? <NotificationBell /> : null}
        {user ? <Badge variant="primary">{user.role}</Badge> : null}
        <Button variant="ghost" size="icon" onClick={toggle} aria-label="Toggle theme">
          {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
        </Button>
        {user ? (
          <>
            <span className="hidden text-sm text-muted-foreground md:inline">{user.email}</span>
            <Button variant="ghost" size="icon" onClick={logout} aria-label="Sign out">
              <LogOut className="h-4 w-4" />
            </Button>
          </>
        ) : null}
      </div>
    </header>
  );
}
