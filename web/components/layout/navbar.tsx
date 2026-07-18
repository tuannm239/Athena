"use client";

import { LogOut, Menu, Moon, Sun } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useTheme } from "@/providers/theme-provider";
import { useAuthStore } from "@/stores/auth-store";

export function Navbar({ onToggleSidebar }: { onToggleSidebar: () => void }) {
  const { theme, toggle } = useTheme();
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);

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

      <div className="ml-auto flex items-center gap-2">
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
