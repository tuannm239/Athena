import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { ThemeProvider } from "@/providers/theme-provider";
import { useAuthStore } from "@/stores/auth-store";

const pathname = { current: "/decisions" };
vi.mock("next/navigation", () => ({ usePathname: () => pathname.current }));

import { AppShell } from "@/components/layout/app-shell";

describe("AppShell", () => {
  it("renders the shell with sidebar and content on app routes", () => {
    useAuthStore.setState({
      status: "authenticated",
      user: { id: "u", email: "a@x.com", status: "active", role: "ANALYST", created_at: "" },
    });
    pathname.current = "/decisions";
    render(
      <ThemeProvider>
        <AppShell><div>page-content</div></AppShell>
      </ThemeProvider>,
    );
    expect(screen.getByText("page-content")).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: /primary/i })).toBeInTheDocument();
  });

  it("bypasses the shell on /login", () => {
    pathname.current = "/login";
    render(
      <ThemeProvider>
        <AppShell><div>bare</div></AppShell>
      </ThemeProvider>,
    );
    expect(screen.getByText("bare")).toBeInTheDocument();
    expect(screen.queryByRole("navigation", { name: /primary/i })).not.toBeInTheDocument();
  });
});
