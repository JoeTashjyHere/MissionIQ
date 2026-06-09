import { Users } from "lucide-react";
import { ModuleGroupStub } from "@/components/ModuleGroupStub";

export default function Page() {
  return (
    <ModuleGroupStub
      group="Organizational Intelligence"
      icon={Users}
      description="Workforce, skills, knowledge, and capability intelligence across the enterprise."
      modules={[
        {
          id: "organizational.skills_map",
          label: "Skills Map",
          description: "Map workforce skills to current and forecast demand.",
        },
        {
          id: "organizational.knowledge_atlas",
          label: "Knowledge Atlas",
          description: "Searchable atlas of organizational knowledge with provenance.",
        },
      ]}
    />
  );
}
