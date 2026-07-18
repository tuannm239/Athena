import { FlaskConical } from "lucide-react";
import { PendingFeature } from "@/features/shared/pending-feature";

export default function Page() {
  return (
    <PendingFeature
      title="Scenario Simulator"
      description="Stress portfolios under macro shocks (SPEC-11)."
      icon={FlaskConical}
      awaits="The scenario simulator (ALG-015) is implemented; the scenario-run API is not yet exposed over REST."
      scope={["Interest Rate Shock","Inflation","FX","Liquidity","Sector Rotation","Custom Scenario","Comparison","Impact Report"]}
    />
  );
}
