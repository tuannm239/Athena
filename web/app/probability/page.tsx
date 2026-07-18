import { Brain } from "lucide-react";
import { PendingFeature } from "@/features/shared/pending-feature";

export default function Page() {
  return (
    <PendingFeature
      title="Probability Studio"
      description="Prior/posterior, evidence weighting and calibration (RFC-0026)."
      icon={Brain}
      awaits="The probability engine runs inside the Decision Kernel; a standalone probability API is not yet exposed over REST."
      scope={["Prior","Posterior","Evidence","Calibration","Reliability","Distribution","Confidence","History"]}
    />
  );
}
