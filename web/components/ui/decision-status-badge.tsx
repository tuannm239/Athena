import { Badge } from "./badge";
import type { DecisionStatus, RiskLevel } from "@/types/api";

const STATUS_VARIANT: Record<DecisionStatus, "muted" | "warn" | "gain" | "loss" | "default"> = {
  DRAFT: "muted",
  UNDER_REVIEW: "warn",
  APPROVED: "gain",
  REJECTED: "loss",
  ARCHIVED: "default",
};

export function DecisionStatusBadge({ status }: { status: DecisionStatus }) {
  return <Badge variant={STATUS_VARIANT[status]}>{status.replace("_", " ")}</Badge>;
}

const RISK_VARIANT: Record<RiskLevel, "gain" | "warn" | "loss"> = {
  VERY_LOW: "gain",
  LOW: "gain",
  MODERATE: "warn",
  HIGH: "loss",
  CRITICAL: "loss",
};

export function RiskLevelBadge({ level }: { level: RiskLevel }) {
  return <Badge variant={RISK_VARIANT[level]}>{level.replace("_", " ")}</Badge>;
}
