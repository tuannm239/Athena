import { Sparkles } from "lucide-react";
import { PendingFeature } from "@/features/shared/pending-feature";

export default function Page() {
  return (
    <PendingFeature
      title="Research Copilot"
      description="Document ingestion, LLM evidence extraction and human review."
      icon={Sparkles}
      awaits="The Research Copilot pipeline (document -> evidence extraction -> KG -> probability) is implemented in the backend but not yet exposed over REST."
      scope={["Documents","News","Evidence Extraction","Evidence Review","Knowledge Graph Links","Research Queue","Human Review","Approval Workflow"]}
    />
  );
}
