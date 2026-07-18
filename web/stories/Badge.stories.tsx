import type { Meta, StoryObj } from "@storybook/react";
import { Badge } from "@/components/ui/badge";

const meta: Meta<typeof Badge> = { title: "UI/Badge", component: Badge, tags: ["autodocs"] };
export default meta;
type Story = StoryObj<typeof Badge>;

export const Default: Story = { args: { children: "Default" } };
export const Primary: Story = { args: { variant: "primary", children: "Primary" } };
export const Gain: Story = { args: { variant: "gain", children: "+2.4%" } };
export const Loss: Story = { args: { variant: "loss", children: "-1.1%" } };
export const Warn: Story = { args: { variant: "warn", children: "Sample data" } };
