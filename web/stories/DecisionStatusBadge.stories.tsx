import type { Meta, StoryObj } from "@storybook/react";
import { DecisionStatusBadge } from "@/components/ui/decision-status-badge";

const meta: Meta<typeof DecisionStatusBadge> = {
  title: "Decision/StatusBadge",
  component: DecisionStatusBadge,
  tags: ["autodocs"],
};
export default meta;
type Story = StoryObj<typeof DecisionStatusBadge>;

export const Draft: Story = { args: { status: "DRAFT" } };
export const UnderReview: Story = { args: { status: "UNDER_REVIEW" } };
export const Approved: Story = { args: { status: "APPROVED" } };
export const Rejected: Story = { args: { status: "REJECTED" } };
