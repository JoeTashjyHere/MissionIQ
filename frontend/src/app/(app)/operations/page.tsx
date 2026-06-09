import { Activity } from "lucide-react";
import { ModuleGroupStub } from "@/components/ModuleGroupStub";

export default function Page() {
  return (
    <ModuleGroupStub
      group="Operations Intelligence"
      icon={Activity}
      description="Deliver: SLA tracking, CDRL compliance, performance posture, and operational risk on active programs."
      modules={[
        {
          id: "operations.sla_tracker",
          label: "SLA Tracker",
          description: "Monitor SLA adherence and surface drift against contract performance standards.",
        },
        {
          id: "operations.cdrl_compliance",
          label: "CDRL Compliance",
          description: "Track CDRL deliverable status and surface late or at-risk submittals.",
        },
        {
          id: "operations.program_health",
          label: "Program Health",
          description: "Executive briefing of program health combining performance, financial, and staffing signals.",
        },
      ]}
    />
  );
}
