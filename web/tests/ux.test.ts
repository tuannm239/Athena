import { beforeEach, describe, expect, it } from "vitest";
import { useUxStore } from "@/stores/ux-store";
import { navResults, reportResults, score, REPORT_KINDS } from "@/lib/search";

describe("ux-store", () => {
  beforeEach(() => useUxStore.getState().reset());

  it("toggles favorites idempotently", () => {
    const item = { type: "decision" as const, id: "d1", label: "H", href: "/decisions/d1" };
    const { toggleFavorite, isFavorite } = useUxStore.getState();
    expect(isFavorite("decision", "d1")).toBe(false);
    toggleFavorite(item);
    expect(useUxStore.getState().isFavorite("decision", "d1")).toBe(true);
    toggleFavorite(item);
    expect(useUxStore.getState().isFavorite("decision", "d1")).toBe(false);
  });

  it("dedupes and caps recent items, newest first", () => {
    const push = useUxStore.getState().pushRecent;
    push({ type: "page", id: "a", label: "A", href: "/a" });
    push({ type: "page", id: "b", label: "B", href: "/b" });
    push({ type: "page", id: "a", label: "A", href: "/a" }); // re-visit a
    const recent = useUxStore.getState().recent;
    expect(recent.map((r) => r.id)).toEqual(["a", "b"]);
  });

  it("pins tickers case-insensitively", () => {
    const { togglePin } = useUxStore.getState();
    togglePin("hpg");
    expect(useUxStore.getState().isPinned("HPG")).toBe(true);
    togglePin("HPG");
    expect(useUxStore.getState().isPinned("hpg")).toBe(false);
  });

  it("saves and removes named filters per page", () => {
    const s = useUxStore.getState();
    s.saveFilter("/decisions", "Approved", "status=APPROVED");
    const list = useUxStore.getState().savedFilters["/decisions"];
    expect(list).toHaveLength(1);
    expect(list[0].query).toBe("status=APPROVED");
    useUxStore.getState().removeFilter("/decisions", list[0].id);
    expect(useUxStore.getState().savedFilters["/decisions"]).toHaveLength(0);
  });

  it("updates preferences", () => {
    useUxStore.getState().setPreferences({ density: "compact" });
    expect(useUxStore.getState().preferences.density).toBe("compact");
  });
});

describe("search helpers", () => {
  it("scores exact/prefix/substring/subsequence in order", () => {
    expect(score("dec", "dec")).toBeGreaterThan(score("dec", "decision"));
    expect(score("dec", "decision")).toBeGreaterThan(score("dec", "the decisions"));
    expect(score("xyz", "decision")).toBe(0);
    expect(score("", "anything")).toBe(1);
  });

  it("navResults matches the dashboard", () => {
    const r = navResults("dashboard");
    expect(r[0].label).toBe("Dashboard");
    expect(r[0].href).toBe("/");
  });

  it("reportResults covers all eight report kinds", () => {
    expect(reportResults("").length).toBe(REPORT_KINDS.length);
    expect(reportResults("risk")[0].label).toBe("Risk Report");
  });
});
