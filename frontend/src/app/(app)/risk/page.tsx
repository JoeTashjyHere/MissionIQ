import { ShieldAlert } from "lucide-react";
import { ModuleGroupStub } from "@/components/ModuleGroupStub";

export default function Page() {
  return (
    <ModuleGroupStub
      group="Risk Intelligence"
      icon={ShieldAlert}
      description="Cross-portfolio risk view: technical, schedule, financial, security, and compliance."
      modules={[
        {
          id: "risk.portfolio_risk",
          label: "Portfolio Risk Register",
          description: "Roll-up of opportunity, program, and operational risks.",
        },
        {
          id: "risk.compliance_posture",
          label: "Compliance Posture",
          description: "Posture across NIST 800-53, FedRAMP, CMMC, and customer-specific controls.",
        },
      ]}
    />
  );
}
