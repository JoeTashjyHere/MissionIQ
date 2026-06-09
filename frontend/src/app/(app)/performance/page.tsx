import { BarChart3 } from "lucide-react";
import { ModuleGroupStub } from "@/components/ModuleGroupStub";

export default function Page() {
  return (
    <ModuleGroupStub
      group="Performance Intelligence"
      icon={BarChart3}
      description="Quantify outcomes across portfolios, programs, and individual contracts."
      modules={[
        {
          id: "performance.portfolio_scorecard",
          label: "Portfolio Scorecard",
          description: "Executive scorecard across all programs in the workspace.",
        },
        {
          id: "performance.contract_health",
          label: "Contract Health Index",
          description: "Composite health score per active contract.",
        },
      ]}
    />
  );
}
