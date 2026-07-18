"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { KeyRound, Copy } from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { authService } from "@/services/auth";
import { useHealth } from "@/hooks/queries";
import { useAuthStore } from "@/stores/auth-store";
import { formatDateTime } from "@/lib/utils";

export default function AdminPage() {
  const isAdmin = useAuthStore((s) => s.hasRole("ADMIN"));
  const qc = useQueryClient();
  const keys = useQuery({ queryKey: ["api-keys"], queryFn: authService.listApiKeys, enabled: isAdmin });
  const health = useHealth();
  const [name, setName] = useState("");
  const [created, setCreated] = useState<string | null>(null);

  const create = useMutation({
    mutationFn: () => authService.createApiKey(name),
    onSuccess: (res) => {
      setCreated(res.api_key);
      setName("");
      void qc.invalidateQueries({ queryKey: ["api-keys"] });
    },
  });
  const revoke = useMutation({
    mutationFn: (id: string) => authService.revokeApiKey(id),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["api-keys"] }),
  });

  if (!isAdmin) {
    return (
      <>
        <PageHeader title="Administration" />
        <EmptyState icon={KeyRound} title="Admins only" description="You need the ADMIN role." />
      </>
    );
  }

  return (
    <>
      <PageHeader title="Administration" description="API keys, health and system metrics." />

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>API Keys</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                if (name.trim()) create.mutate();
              }}
              className="flex gap-2"
            >
              <input
                aria-label="API key name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Key name (e.g. ci-pipeline)"
                className="h-9 flex-1 rounded-md border bg-background px-3 text-sm focus-visible:ring-2 focus-visible:ring-ring"
              />
              <Button type="submit" disabled={create.isPending || !name.trim()}>
                Create
              </Button>
            </form>

            {created ? (
              <div className="rounded-md border border-warn/40 bg-warn/10 p-3 text-xs">
                <p className="mb-1 font-medium text-warn">Copy this key now — it is shown once.</p>
                <code className="flex items-center gap-2 break-all font-mono">
                  {created}
                  <Copy
                    className="h-3 w-3 shrink-0 cursor-pointer"
                    onClick={() => navigator.clipboard?.writeText(created)}
                  />
                </code>
              </div>
            ) : null}

            {keys.isLoading ? (
              <Skeleton className="h-24 w-full" />
            ) : keys.data && keys.data.length > 0 ? (
              <ul className="divide-y">
                {keys.data.map((k) => (
                  <li key={k.id} className="flex items-center justify-between gap-2 py-2 text-sm">
                    <div>
                      <p className="font-medium">{k.name}</p>
                      <p className="text-xs text-muted-foreground">
                        {k.prefix}… · {formatDateTime(k.created_at)}
                      </p>
                    </div>
                    {k.revoked_at ? (
                      <Badge variant="muted">revoked</Badge>
                    ) : (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => revoke.mutate(k.id)}
                        disabled={revoke.isPending}
                      >
                        Revoke
                      </Button>
                    )}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-muted-foreground">No API keys yet.</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>System Health</CardTitle>
          </CardHeader>
          <CardContent>
            {health.isLoading ? (
              <Skeleton className="h-24 w-full" />
            ) : health.data ? (
              <div className="space-y-2">
                <Badge variant={health.data.status === "ok" ? "gain" : "warn"}>
                  {health.data.status.toUpperCase()} · v{health.data.version}
                </Badge>
                <ul className="space-y-1 text-sm">
                  {Object.entries(health.data.components).map(([k, v]) => (
                    <li key={k} className="flex justify-between">
                      <span className="text-muted-foreground">{k}</span>
                      <span className={v === "ok" ? "text-gain" : "text-warn"}>{v}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">Health unavailable.</p>
            )}
          </CardContent>
        </Card>
      </div>
    </>
  );
}
