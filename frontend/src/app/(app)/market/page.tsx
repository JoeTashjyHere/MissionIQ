import { Globe2 } from "lucide-react";
import { ModuleGroupStub } from "@/components/ModuleGroupStub";

export default function Page() {
  return (
    <ModuleGroupStub
      group="Market Intelligence"
      icon={Globe2}
      description="Cross-pursuit market intelligence: agency buying patterns, NAICS posture, vehicle trends."
      modules={[
        {
          id: "market.agency_buying_signals",
          label: "Agency Buying Signals",
          description: "Detect agency-level buying patterns from public market data.",
        },
        {
          id: "market.vehicle_landscape",
          label: "Vehicle Landscape",
          description: "Track GWAC / IDIQ / BPA activity across the workspace's pursuit footprint.",
        },
      ]}
    />
  );
}
