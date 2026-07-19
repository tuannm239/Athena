import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Spinner } from "@/components/ui/spinner";
import { EmptyState } from "@/components/ui/empty-state";
import { PageHeader } from "@/components/layout/page-header";
import { Target } from "lucide-react";
import { NAV_SECTIONS } from "@/lib/navigation";

describe("primitives", () => {
  it("Button fires onClick and respects disabled", async () => {
    const onClick = vi.fn();
    const { rerender } = render(<Button onClick={onClick}>Go</Button>);
    await userEvent.click(screen.getByRole("button", { name: "Go" }));
    expect(onClick).toHaveBeenCalledOnce();
    rerender(<Button disabled onClick={onClick}>Go</Button>);
    await userEvent.click(screen.getByRole("button", { name: "Go" }));
    expect(onClick).toHaveBeenCalledOnce();
  });

  it("Card composition renders title and content", () => {
    render(
      <Card><CardHeader><CardTitle>Head</CardTitle></CardHeader><CardContent>Body</CardContent></Card>,
    );
    expect(screen.getByText("Head")).toBeInTheDocument();
    expect(screen.getByText("Body")).toBeInTheDocument();
  });

  it("Skeleton and Spinner render", () => {
    render(<><Skeleton className="h-4" /><Spinner /></>);
    expect(screen.getByRole("status")).toBeInTheDocument();
  });

  it("EmptyState renders icon, title, description, action", () => {
    render(<EmptyState icon={Target} title="Nothing" description="here" action={<span>act</span>} />);
    expect(screen.getByText("Nothing")).toBeInTheDocument();
    expect(screen.getByText("here")).toBeInTheDocument();
    expect(screen.getByText("act")).toBeInTheDocument();
  });

  it("PageHeader renders title, description and actions", () => {
    render(<PageHeader title="T" description="D" actions={<button>A</button>} />);
    expect(screen.getByRole("heading", { name: "T" })).toBeInTheDocument();
    expect(screen.getByText("D")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "A" })).toBeInTheDocument();
  });

  it("navigation covers the core destinations across sections", () => {
    expect(NAV_SECTIONS).toHaveLength(5);
    const hrefs = NAV_SECTIONS.flatMap((s) => s.items.map((i) => i.href));
    expect(hrefs).toEqual(
      expect.arrayContaining([
        "/", "/decisions", "/companies", "/watchlist", "/portfolio", "/research",
        "/evidence", "/knowledge-graph", "/feature-store", "/probability", "/backtest",
        "/scenario", "/market", "/reports", "/admin", "/settings", "/profile",
        "/help", "/feedback", "/about",
      ]),
    );
    const admin = NAV_SECTIONS.flatMap((s) => s.items).find((i) => i.href === "/admin");
    expect(admin?.roles).toEqual(["ADMIN"]);
  });
});
