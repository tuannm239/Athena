import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { Badge } from "@/components/ui/badge";
import { Gauge } from "@/components/ui/gauge";
import { DecisionStatusBadge, RiskLevelBadge } from "@/components/ui/decision-status-badge";
import { EvidenceCard } from "@/components/ui/evidence-card";
import { Stat } from "@/components/ui/stat";
import type { EvidenceOut } from "@/types/api";

describe("UI components", () => {
  it("Badge renders children", () => {
    render(<Badge>Hello</Badge>);
    expect(screen.getByText("Hello")).toBeInTheDocument();
  });

  it("Gauge clamps and exposes an accessible label", () => {
    render(<Gauge value={1.5} label="confidence" />);
    // clamps to 100%
    expect(screen.getByRole("img", { name: /confidence: 100%/i })).toBeInTheDocument();
  });

  it("DecisionStatusBadge maps status to readable text", () => {
    render(<DecisionStatusBadge status="UNDER_REVIEW" />);
    expect(screen.getByText("UNDER REVIEW")).toBeInTheDocument();
  });

  it("RiskLevelBadge renders the level", () => {
    render(<RiskLevelBadge level="CRITICAL" />);
    expect(screen.getByText("CRITICAL")).toBeInTheDocument();
  });

  it("Stat renders label and value", () => {
    render(<Stat label="Total" value={42} />);
    expect(screen.getByText("Total")).toBeInTheDocument();
    expect(screen.getByText("42")).toBeInTheDocument();
  });

  it("EvidenceCard shows direction, reliability and LLM provenance", () => {
    const ev: EvidenceOut = {
      id: "1", source: "report:x", category: "financial",
      explanation: "Revenue grew", reliability: "0.8", direction: "SUPPORTING",
      metadata: { source_type: "llm", model: "fake-llm" }, timestamp: "",
    };
    render(<EvidenceCard evidence={ev} />);
    expect(screen.getByText("Revenue grew")).toBeInTheDocument();
    expect(screen.getByText(/Reliability 80%/)).toBeInTheDocument();
    expect(screen.getByText(/LLM-extracted/)).toBeInTheDocument();
  });
});
