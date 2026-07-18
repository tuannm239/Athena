import type { Meta, StoryObj } from "@storybook/react";
import { Gauge } from "@/components/ui/gauge";

const meta: Meta<typeof Gauge> = { title: "UI/Gauge", component: Gauge, tags: ["autodocs"] };
export default meta;
type Story = StoryObj<typeof Gauge>;

export const Probability: Story = { args: { value: 0.72, label: "probability" } };
export const Confidence: Story = { args: { value: 0.41, label: "confidence", tone: "gain" } };
export const HighRisk: Story = { args: { value: 0.88, label: "risk", tone: "loss" } };
