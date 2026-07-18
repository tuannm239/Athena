import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "@/providers/theme-provider";
import { useAuthStore } from "@/stores/auth-store";

const pathname = { current: "/decisions" };
vi.mock("next/navigation", () => ({
  usePathname: () => pathname.current,
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), prefetch: vi.fn() }),
}));

import { AppShell } from "@/components/layout/app-shell";

function wrap(children: ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return (
    <QueryClientProvider client={qc}>
      <ThemeProvider>{children}</ThemeProvider>
    </QueryClientProvider>
  );
}

describe("AppShell", () => {
  it("renders the shell with sidebar and content on app routes", () => {
    useAuthStore.setState({
      status: "authenticated",
      user: { id: "u", email: "a@x.com", status: "active", role: "ANALYST", created_at: "" },
    });
    pathname.current = "/decisions";
    render(wrap(<AppShell><div>page-content</div></AppShell>));
    expect(screen.getByText("page-content")).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: /primary/i })).toBeInTheDocument();
  });

  it("bypasses the shell on /login", () => {
    pathname.current = "/login";
    render(wrap(<AppShell><div>bare</div></AppShell>));
    expect(screen.getByText("bare")).toBeInTheDocument();
    expect(screen.queryByRole("navigation", { name: /primary/i })).not.toBeInTheDocument();
  });
});
