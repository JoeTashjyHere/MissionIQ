import { GitBranch } from "lucide-react";
import { ModuleGroupStub } from "@/components/ModuleGroupStub";

export default function Page() {
  return (
    <ModuleGroupStub
      group="Process Intelligence"
      icon={GitBranch}
      description="Improve: process discovery, bottleneck analysis, and continuous-improvement intelligence."
      modules={[
        {
          id: "process.bottleneck_analysis",
          label: "Bottleneck Analysis",
          description: "Identify and prioritize process bottlenecks across operational pipelines.",
        },
        {
          id: "process.maturity_assessment",
          label: "Process Maturity",
          description: "Assess CMMI / NIST-aligned maturity across the organization.",
        },
      ]}
    />
  );
}
