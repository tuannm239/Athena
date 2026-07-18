import type { Meta, StoryObj } from "@storybook/react";
import { EvidenceCard } from "@/components/ui/evidence-card";

const meta: Meta<typeof EvidenceCard> = {
  title: "Decision/EvidenceCard",
  component: EvidenceCard,
  tags: ["autodocs"],
};
export default meta;
type Story = StoryObj<typeof EvidenceCard>;

export const Supporting: Story = {
  args: {
    evidence: {
      id: "1", source: "annual-report:2025", category: "financial",
      explanation: "Revenue grew 30% YoY with expanding margins.",
      reliability: "0.82", direction: "SUPPORTING", metadata: {}, timestamp: "",
    },
  },
};
export const ContradictingFromLlm: Story = {
  args: {
    evidence: {
      id: "2", source: "news:reuters", category: "liquidity",
      explanation: "Free float below the exchange minimum threshold.",
      reliability: "0.6", direction: "CONTRADICTING",
      metadata: { source_type: "llm", model: "claude-sonnet-5" }, timestamp: "",
    },
  },
};
