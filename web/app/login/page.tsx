"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { useAuthStore } from "@/stores/auth-store";
import { authService } from "@/services/auth";
import { ApiRequestError } from "@/lib/api-client";
import { toast } from "@/stores/toast-store";

type Mode = "login" | "register";

export default function LoginPage() {
  const router = useRouter();
  const login = useAuthStore((s) => s.login);
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      if (mode === "register") {
        await authService.register(email, password);
        toast.success("Account created. Welcome to Athena.");
      }
      await login(email, password);
      router.replace("/");
    } catch (err) {
      if (mode === "register" && err instanceof ApiRequestError && err.status === 409) {
        setError("An account with this email already exists. Try signing in.");
      } else if (err instanceof ApiRequestError && err.status === 401) {
        setError("Invalid email or password.");
      } else {
        setError(mode === "register" ? "Registration failed. Please try again." : "Sign-in failed.");
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <div className="w-full max-w-sm">
        <div className="mb-6 flex items-center justify-center gap-2">
          <div className="flex h-9 w-9 items-center justify-center rounded bg-primary text-lg font-bold text-primary-foreground">
            A
          </div>
          <div>
            <p className="font-semibold tracking-tight">ATHENA</p>
            <p className="text-xs text-muted-foreground">Decision Intelligence</p>
          </div>
        </div>
        <Card>
          <CardContent className="p-6">
            <div className="mb-4 flex rounded-md border p-0.5 text-sm" role="tablist">
              {(["login", "register"] as Mode[]).map((m) => (
                <button
                  key={m}
                  role="tab"
                  aria-selected={mode === m}
                  onClick={() => {
                    setMode(m);
                    setError(null);
                  }}
                  className={`flex-1 rounded px-3 py-1.5 transition-colors ${
                    mode === m ? "bg-primary text-primary-foreground" : "text-muted-foreground"
                  }`}
                >
                  {m === "login" ? "Sign in" : "Register"}
                </button>
              ))}
            </div>
            <form onSubmit={onSubmit} className="space-y-4" aria-label={mode === "login" ? "Sign in" : "Register"}>
              <div className="space-y-1">
                <label htmlFor="email" className="text-sm font-medium">
                  Email
                </label>
                <input
                  id="email"
                  type="email"
                  autoComplete="username"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="h-9 w-full rounded-md border bg-background px-3 text-sm focus-visible:ring-2 focus-visible:ring-ring"
                />
              </div>
              <div className="space-y-1">
                <label htmlFor="password" className="text-sm font-medium">
                  Password
                </label>
                <input
                  id="password"
                  type="password"
                  autoComplete={mode === "login" ? "current-password" : "new-password"}
                  required
                  minLength={mode === "register" ? 8 : undefined}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="h-9 w-full rounded-md border bg-background px-3 text-sm focus-visible:ring-2 focus-visible:ring-ring"
                />
                {mode === "register" ? (
                  <p className="text-xs text-muted-foreground">At least 8 characters.</p>
                ) : null}
              </div>
              {error ? (
                <p role="alert" className="text-sm text-loss">
                  {error}
                </p>
              ) : null}
              <Button type="submit" className="w-full" disabled={busy}>
                {busy ? <Spinner /> : null}
                {mode === "login" ? "Sign in" : "Create account"}
              </Button>
            </form>
          </CardContent>
        </Card>
        <p className="mt-4 text-center text-xs text-muted-foreground">
          Athena assists human decisions. Every recommendation requires your approval.
        </p>
      </div>
    </div>
  );
}
