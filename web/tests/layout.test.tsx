import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { Sidebar } from "@/components/layout/sidebar";
import { Navbar } from "@/components/layout/navbar";
import { ThemeProvider } from "@/providers/theme-provider";
import { useAuthStore } from "@/stores/auth-store";

vi.mock("next/navigation", () => ({ usePathname: () => "/decisions" }));

describe("layout", () => {
  beforeEach(() => {
    useAuthStore.setState({
      status: "authenticated",
      user: { id: "u", email: "a@x.com", status: "active", role: "ANALYST", created_at: "" },
    });
  });

  it("Sidebar hides admin-only items for non-admins", () => {
    render(<Sidebar />);
    expect(screen.getByText("Decision Center")).toBeInTheDocument();
    expect(screen.queryByText("Administration")).not.toBeInTheDocument();
  });

  it("Sidebar shows admin items for admins", () => {
    useAuthStore.setState({
      status: "authenticated",
      user: { id: "u", email: "a@x.com", status: "active", role: "ADMIN", created_at: "" },
    });
    render(<Sidebar />);
    expect(screen.getByText("Administration")).toBeInTheDocument();
  });

  it("Navbar shows the user email and role", () => {
    render(
      <ThemeProvider>
        <Navbar onToggleSidebar={() => {}} />
      </ThemeProvider>,
    );
    expect(screen.getByText("a@x.com")).toBeInTheDocument();
    expect(screen.getByText("ANALYST")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /toggle theme/i })).toBeInTheDocument();
  });
});
