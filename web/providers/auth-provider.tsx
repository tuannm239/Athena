"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuthStore } from "@/stores/auth-store";

const PUBLIC_ROUTES = ["/login"];

/** Bootstraps the session on load and guards non-public routes. */
export function AuthProvider({ children }: { children: React.ReactNode }) {
  const status = useAuthStore((s) => s.status);
  const bootstrap = useAuthStore((s) => s.bootstrap);
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    void bootstrap();
  }, [bootstrap]);

  useEffect(() => {
    if (status === "anonymous" && !PUBLIC_ROUTES.includes(pathname)) {
      router.replace("/login");
    }
  }, [status, pathname, router]);

  if (status === "loading" && !PUBLIC_ROUTES.includes(pathname)) {
    return (
      <div className="flex h-screen items-center justify-center text-muted-foreground">
        <div className="animate-pulse text-sm">Loading Athena…</div>
      </div>
    );
  }

  return <>{children}</>;
}
