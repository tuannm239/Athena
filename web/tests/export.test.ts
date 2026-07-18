import { describe, expect, it } from "vitest";
import { toCSV, type Column } from "@/lib/export";

interface Row {
  a: string;
  b: number;
}
const columns: Column<Row>[] = [
  { header: "A", accessor: (r) => r.a },
  { header: "B", accessor: (r) => r.b },
];

describe("toCSV", () => {
  it("emits a header row and one line per record", () => {
    const csv = toCSV(columns, [
      { a: "x", b: 1 },
      { a: "y", b: 2 },
    ]);
    expect(csv).toBe("A,B\nx,1\ny,2\n");
  });

  it("quotes and escapes fields containing commas, quotes and newlines", () => {
    const csv = toCSV([{ header: "V", accessor: (r: { v: string }) => r.v }], [
      { v: 'a,b' },
      { v: 'he said "hi"' },
      { v: "line1\nline2" },
    ]);
    expect(csv).toContain('"a,b"');
    expect(csv).toContain('"he said ""hi"""');
    expect(csv).toContain('"line1\nline2"');
  });

  it("renders null/undefined as empty cells", () => {
    const csv = toCSV(
      [{ header: "V", accessor: (r: { v: string | null }) => r.v }],
      [{ v: null }],
    );
    expect(csv).toBe("V\n\n");
  });
});
