import { Network } from "lucide-react";
import { PendingFeature } from "@/features/shared/pending-feature";

export default function Page() {
  return (
    <PendingFeature
      title="Knowledge Graph"
      description="Interactive company/sector/evidence graph (RFC-0019)."
      icon={Network}
      awaits="Graph traversal services exist in the backend; the read API surface for nodes/edges is not yet exposed over REST."
      scope={["Interactive Graph","Nodes","Edges","Traversal","Relationship Explorer","Impact Explorer","Evidence Links","Filters","Search","Mini Map"]}
    />
  );
}
