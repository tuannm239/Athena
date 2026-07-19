"use client";

import { Moon, Sun, Star, Pin, Clock, Trash2, Globe, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { PageHeader } from "@/components/layout/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { useTheme } from "@/providers/theme-provider";
import { useUxStore, type Density } from "@/stores/ux-store";
import { useAuthStore } from "@/stores/auth-store";
import { NAV_SECTIONS } from "@/lib/navigation";

function Toggle({
  label,
  description,
  checked,
  onChange,
}: {
  label: string;
  description?: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <div className="flex items-center justify-between gap-4">
      <div>
        <p className="text-sm font-medium">{label}</p>
        {description ? <p className="text-xs text-muted-foreground">{description}</p> : null}
      </div>
      <button
        role="switch"
        aria-checked={checked}
        aria-label={label}
        onClick={() => onChange(!checked)}
        className={`relative h-6 w-11 shrink-0 rounded-full transition-colors ${
          checked ? "bg-primary" : "bg-muted"
        }`}
      >
        <span
          className={`absolute top-0.5 h-5 w-5 rounded-full bg-background shadow transition-transform ${
            checked ? "translate-x-[22px]" : "translate-x-0.5"
          }`}
        />
      </button>
    </div>
  );
}

export default function SettingsPage() {
  const { theme, setTheme } = useTheme();
  const isAdmin = useAuthStore((s) => s.hasRole("ADMIN"));
  const prefs = useUxStore((s) => s.preferences);
  const setPreferences = useUxStore((s) => s.setPreferences);
  const favorites = useUxStore((s) => s.favorites);
  const pinned = useUxStore((s) => s.pinnedCompanies);
  const recent = useUxStore((s) => s.recent);
  const toggleFavorite = useUxStore((s) => s.toggleFavorite);
  const togglePin = useUxStore((s) => s.togglePin);
  const clearRecent = useUxStore((s) => s.clearRecent);

  const allPages = NAV_SECTIONS.flatMap((s) => s.items);

  return (
    <>
      <PageHeader title="Settings" description="Appearance, preferences, and personalization." />

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Appearance</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex gap-2">
              <Button
                variant={theme === "dark" ? "default" : "outline"}
                onClick={() => setTheme("dark")}
              >
                <Moon className="h-4 w-4" /> Dark
              </Button>
              <Button
                variant={theme === "light" ? "default" : "outline"}
                onClick={() => setTheme("light")}
              >
                <Sun className="h-4 w-4" /> Light
              </Button>
            </div>
            <div>
              <p className="mb-2 text-sm font-medium">Density</p>
              <div className="flex gap-2">
                {(["comfortable", "compact"] as Density[]).map((d) => (
                  <Button
                    key={d}
                    variant={prefs.density === d ? "default" : "outline"}
                    size="sm"
                    onClick={() => setPreferences({ density: d })}
                  >
                    {d}
                  </Button>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Preferences</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <Toggle
              label="Show sample data"
              description="Display clearly-labelled sample data when a live feed is unavailable."
              checked={prefs.showSampleData}
              onChange={(v) => setPreferences({ showSampleData: v })}
            />
            <Toggle
              label="Reduce motion"
              description="Minimize non-essential animation."
              checked={prefs.reduceMotion}
              onChange={(v) => setPreferences({ reduceMotion: v })}
            />
            <div>
              <p className="mb-2 text-sm font-medium">Landing page</p>
              <select
                value={prefs.landingPage}
                onChange={(e) => setPreferences({ landingPage: e.target.value })}
                className="h-9 w-full rounded-md border bg-background px-3 text-sm"
                aria-label="Landing page"
              >
                {allPages.map((p) => (
                  <option key={p.href} value={p.href}>
                    {p.label}
                  </option>
                ))}
              </select>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Globe className="h-4 w-4" /> Language &amp; Accessibility
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <p className="mb-2 text-sm font-medium">Language</p>
              <select
                value={prefs.language}
                onChange={(e) => setPreferences({ language: e.target.value as "en" | "vi" })}
                className="h-9 w-full rounded-md border bg-background px-3 text-sm"
                aria-label="Language"
              >
                <option value="en">English</option>
                <option value="vi">Tiếng Việt</option>
              </select>
              <p className="mt-1 text-xs text-muted-foreground">
                Vietnamese localization of interface copy is rolling out; the preference is saved now.
              </p>
            </div>
            <Toggle
              label="High contrast"
              description="Increase contrast for readability."
              checked={prefs.highContrast}
              onChange={(v) => setPreferences({ highContrast: v })}
            />
            <p className="text-xs text-muted-foreground">
              Keyboard navigation, visible focus rings and a skip-to-content link are always on.
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ShieldCheck className="h-4 w-4" /> Security &amp; Notifications
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <p className="text-muted-foreground">
              Sessions use short-lived tokens with automatic refresh; RBAC is enforced on the server.
            </p>
            <div className="flex flex-wrap gap-3">
              <Link href="/notifications" className="text-primary hover:underline">
                Notifications
              </Link>
              {isAdmin ? (
                <Link href="/admin" className="text-primary hover:underline">
                  API keys &amp; administration
                </Link>
              ) : (
                <span className="text-muted-foreground">API keys are managed by an administrator.</span>
              )}
              <Link href="/profile" className="text-primary hover:underline">
                Profile
              </Link>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex-row items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <Star className="h-4 w-4" /> Favorites
            </CardTitle>
          </CardHeader>
          <CardContent>
            {favorites.length === 0 ? (
              <EmptyState title="No favorites yet" description="Star decisions, companies or reports to pin them here." />
            ) : (
              <ul className="divide-y">
                {favorites.map((f) => (
                  <li key={`${f.type}-${f.id}`} className="flex items-center justify-between gap-2 py-2">
                    <Link href={f.href} className="min-w-0 flex-1 truncate text-sm hover:underline">
                      {f.label}
                    </Link>
                    <span className="text-xs text-muted-foreground">{f.type}</span>
                    <Button variant="ghost" size="icon" aria-label="Remove" onClick={() => toggleFavorite(f)}>
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex-row items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <Pin className="h-4 w-4" /> Pinned companies
            </CardTitle>
          </CardHeader>
          <CardContent>
            {pinned.length === 0 ? (
              <EmptyState title="No pinned companies" description="Pin tickers for quick access from the dashboard." />
            ) : (
              <div className="flex flex-wrap gap-2">
                {pinned.map((t) => (
                  <button
                    key={t}
                    onClick={() => togglePin(t)}
                    className="inline-flex items-center gap-1 rounded-full border px-3 py-1 text-xs hover:bg-accent"
                    title={`Unpin ${t}`}
                  >
                    <Pin className="h-3 w-3 fill-primary text-primary" /> {t}
                  </button>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader className="flex-row items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <Clock className="h-4 w-4" /> Recent items
            </CardTitle>
            {recent.length > 0 ? (
              <Button variant="outline" size="sm" onClick={clearRecent}>
                Clear
              </Button>
            ) : null}
          </CardHeader>
          <CardContent>
            {recent.length === 0 ? (
              <EmptyState title="Nothing recent" description="Pages and entities you open will appear here." />
            ) : (
              <ul className="grid gap-1 sm:grid-cols-2">
                {recent.map((r) => (
                  <li key={`${r.type}-${r.id}`}>
                    <Link
                      href={r.href}
                      className="flex items-center justify-between gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-accent"
                    >
                      <span className="min-w-0 flex-1 truncate">{r.label}</span>
                      <span className="text-xs text-muted-foreground">{r.type}</span>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>
    </>
  );
}
