import { Boxes } from "lucide-react";
import { PendingFeature } from "@/features/shared/pending-feature";

export default function Page() {
  return (
    <PendingFeature
      title="Feature Store"
      description="Feature catalogue, versions and lineage (RFC-0023)."
      icon={Boxes}
      awaits="The feature registry and factor catalogue are implemented; the browse/search API is not yet exposed over REST."
      scope={["Feature List","Feature Metadata","Feature Version","Lineage","Dependencies","History","Quality","Search"]}
    />
  );
}
