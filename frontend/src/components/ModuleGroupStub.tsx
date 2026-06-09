import { PageHeader } from "@/components/PageHeader";
import { Card, CardBody } from "@/components/ds/Card";
import type { LucideIcon } from "lucide-react";

export function ModuleGroupStub({
  group,
  icon: Icon,
  description,
  modules,
}: {
  group: string;
  icon: LucideIcon;
  description: string;
  modules: { id: string; label: string; description: string }[];
}) {
  return (
    <div>
      <PageHeader
        eyebrow="MissionIQ"
        title={group}
        subtitle={description}
      />
      <Card>
        <CardBody>
          <div className="flex items-start gap-4">
            <div className="rounded-md bg-steel-700/10 p-3 text-steel-700">
              <Icon className="h-7 w-7" />
            </div>
            <div>
              <div className="text-h3 text-charcoal-900">Planned modules</div>
              <p className="text-charcoal-500 text-[14px] mt-1 mb-4">
                These modules are scheduled in the platform roadmap. Each will
                snap into the existing module registry, RAG engine, LLM router,
                and design system — no architectural changes required.
              </p>
              <ul className="divide-y divide-charcoal-100 border border-charcoal-300 rounded-md bg-white">
                {modules.map((m) => (
                  <li key={m.id} className="px-4 py-3">
                    <div className="font-medium text-charcoal-900">{m.label}</div>
                    <div className="text-[12px] text-charcoal-500 font-mono">{m.id}</div>
                    <p className="text-[13px] text-charcoal-700 mt-1">{m.description}</p>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </CardBody>
      </Card>
    </div>
  );
}
