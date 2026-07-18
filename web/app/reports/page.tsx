import { FileText } from "lucide-react";
import { PendingFeature } from "@/features/shared/pending-feature";

export default function Page() {
  return (
    <PendingFeature
      title="Reports"
      description="Decision, portfolio, risk and validation reports."
      icon={FileText}
      awaits="Report generation/export endpoints are not yet exposed over REST."
      scope={["Decision Reports","Portfolio Reports","Risk Reports","Research Reports","Validation Reports","Export PDF","Export Excel","Export CSV"]}
    />
  );
}
