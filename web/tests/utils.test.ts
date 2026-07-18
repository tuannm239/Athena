import { describe, expect, it } from "vitest";
import { cn, pct, money, num, signClass, formatDate } from "@/lib/utils";

describe("utils", () => {
  it("cn merges and dedupes tailwind classes", () => {
    expect(cn("p-2", "p-4")).toBe("p-4");
    expect(cn("text-sm", false && "hidden", "font-bold")).toBe("text-sm font-bold");
  });

  it("pct formats decimal strings as percentages", () => {
    expect(pct("0.5")).toBe("50.0%");
    expect(pct(0.1234, 2)).toBe("12.34%");
    expect(pct(null)).toBe("—");
    expect(pct("")).toBe("—");
    expect(pct("not-a-number")).toBe("—");
  });

  it("num formats with fixed digits", () => {
    expect(num("1234.5", 2)).toBe("1,234.50");
    expect(num(null)).toBe("—");
  });

  it("money formats currency", () => {
    expect(money("1000000", "VND")).toContain("1,000,000");
    expect(money(null)).toBe("—");
  });

  it("signClass returns gain/loss/muted", () => {
    expect(signClass("1")).toBe("text-gain");
    expect(signClass("-1")).toBe("text-loss");
    expect(signClass("0")).toBe("text-muted-foreground");
    expect(signClass(null)).toBe("text-muted-foreground");
  });

  it("formatDate handles bad input", () => {
    expect(formatDate(null)).toBe("—");
    expect(formatDate("garbage")).toBe("—");
  });
});

import { formatDateTime } from "@/lib/utils";
describe("formatDateTime", () => {
  it("formats and guards bad input", () => {
    expect(formatDateTime(null)).toBe("—");
    expect(formatDateTime("nope")).toBe("—");
    expect(formatDateTime("2026-07-18T10:00:00Z")).toContain("2026");
  });
});
