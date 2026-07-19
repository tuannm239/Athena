"use client";

import { useMemo, useState } from "react";
import { Boxes, Search } from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";

interface Feature {
  id: string;
  name: string;
  category: "Profitability" | "Leverage" | "Liquidity" | "Valuation" | "Growth" | "Cash" | "Market";
  unit: string;
  description: string;
}

// The catalogue of features Athena actually computes (WS2 fundamentals +
// market factors). This is the real feature set, browsable and searchable.
const FEATURES: Feature[] = [
  { id: "roe", name: "ROE", category: "Profitability", unit: "%", description: "Net income / total equity." },
  { id: "roa", name: "ROA", category: "Profitability", unit: "%", description: "Net income / total assets." },
  { id: "gross_margin", name: "Gross margin", category: "Profitability", unit: "%", description: "Gross profit / revenue." },
  { id: "operating_margin", name: "Operating margin", category: "Profitability", unit: "%", description: "Operating income / revenue." },
  { id: "net_margin", name: "Net margin", category: "Profitability", unit: "%", description: "Net income / revenue." },
  { id: "debt_to_equity", name: "Debt / Equity", category: "Leverage", unit: "x", description: "Interest-bearing debt (or total liabilities) / equity." },
  { id: "current_ratio", name: "Current ratio", category: "Liquidity", unit: "x", description: "Current assets / current liabilities." },
  { id: "fcf", name: "Free cash flow", category: "Cash", unit: "VND", description: "Operating cash flow − capex." },
  { id: "eps", name: "EPS", category: "Valuation", unit: "VND", description: "Net income / shares outstanding." },
  { id: "bvps", name: "BVPS", category: "Valuation", unit: "VND", description: "Total equity / shares outstanding." },
  { id: "pe", name: "P/E", category: "Valuation", unit: "x", description: "Price / earnings per share." },
  { id: "pb", name: "P/B", category: "Valuation", unit: "x", description: "Price / book value per share." },
  { id: "ev_ebitda", name: "EV/EBITDA", category: "Valuation", unit: "x", description: "Enterprise value / EBITDA." },
  { id: "revenue_growth", name: "Revenue growth (YoY)", category: "Growth", unit: "%", description: "Year-over-year revenue growth." },
  { id: "eps_growth", name: "EPS growth (YoY)", category: "Growth", unit: "%", description: "Year-over-year EPS growth." },
  { id: "quality_score", name: "Quality score", category: "Profitability", unit: "0-100", description: "Blended profitability, strength and cash quality." },
  { id: "valuation_score", name: "Valuation score", category: "Valuation", unit: "0-100", description: "Reward for reasonable P/E and P/B." },
  { id: "growth_score", name: "Growth score", category: "Growth", unit: "0-100", description: "Blended revenue and EPS growth." },
  { id: "liquidity_score", name: "Liquidity (market)", category: "Market", unit: "0-100", description: "Market-wide matched value / turnover." },
  { id: "breadth_score", name: "Breadth", category: "Market", unit: "0-100", description: "Advancers vs decliners." },
  { id: "volatility_score", name: "Volatility", category: "Market", unit: "0-100", description: "Realized market volatility." },
  { id: "rotation_score", name: "Rotation", category: "Market", unit: "0-100", description: "Sector-rotation intensity." },
];

const CATEGORIES = ["All", ...Array.from(new Set(FEATURES.map((f) => f.category)))];

export default function FeatureStorePage() {
  const [q, setQ] = useState("");
  const [cat, setCat] = useState("All");

  const filtered = useMemo(
    () =>
      FEATURES.filter(
        (f) =>
          (cat === "All" || f.category === cat) &&
          (q === "" ||
            `${f.name} ${f.description}`.toLowerCase().includes(q.toLowerCase())),
      ),
    [q, cat],
  );

  return (
    <>
      <PageHeader
        title="Feature Store"
        description="The catalogue of features Athena computes for Vietnamese equities and the market (SPEC-07 Feature Store)."
      />

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <div className="flex items-center gap-2 rounded-md border bg-background px-3">
          <Search className="h-4 w-4 text-muted-foreground" />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search features…"
            className="h-9 bg-transparent text-sm outline-none"
            aria-label="Search features"
          />
        </div>
        <div className="flex flex-wrap gap-1">
          {CATEGORIES.map((c) => (
            <button
              key={c}
              onClick={() => setCat(c)}
              className={`rounded-full border px-3 py-1 text-xs ${
                cat === c ? "bg-primary text-primary-foreground" : "hover:bg-accent"
              }`}
            >
              {c}
            </button>
          ))}
        </div>
      </div>

      {filtered.length === 0 ? (
        <EmptyState icon={Boxes} title="No matching features" />
      ) : (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {filtered.map((f) => (
            <Card key={f.id}>
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <span className="font-medium">{f.name}</span>
                  <Badge variant="muted">{f.category}</Badge>
                </div>
                <p className="mt-1 text-xs text-muted-foreground">{f.description}</p>
                <p className="mt-2 text-[10px] uppercase tracking-wide text-muted-foreground">
                  unit: {f.unit}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
      <p className="mt-4 text-xs text-muted-foreground">
        Showing {filtered.length} of {FEATURES.length} features.
      </p>
    </>
  );
}
