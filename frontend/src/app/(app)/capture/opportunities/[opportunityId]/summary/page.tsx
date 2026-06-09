"use client";

import { use } from "react";
import { PageHeader } from "@/components/PageHeader";
import { ModuleWorkbench } from "@/components/intelligence/ModuleWorkbench";
import { BriefingSection, BulletList } from "@/components/ds/BriefingSection";

interface SummaryOutput {
  executive_summary?: string;
  mission_need?: string;
  scope_summary?: string;
  key_services?: string[];
  deliverables?: string[];
  timeline?: string;
  risks?: string[];
  pursue_indicators?: string[];
  no_pursue_indicators?: string[];
  key_findings?: string[];
  recommended_actions?: string[];
  _notice?: string;
}

function renderSummary(json: Record<string, unknown>) {
  const o = json as SummaryOutput;
  return (
    <div className="-mx-6">
      {o._notice && (
        <div className="mx-6 mb-3 rounded-md bg-steel-700/10 text-steel-700 text-[12px] px-3 py-2">
          {o._notice}
        </div>
      )}
      <BriefingSection eyebrow="Executive Summary" title="Bottom line">
        <p>{o.executive_summary || "—"}</p>
      </BriefingSection>
      <BriefingSection eyebrow="Mission" title="Mission need & scope">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Block label="Mission need" body={o.mission_need} />
          <Block label="Scope summary" body={o.scope_summary} />
        </div>
      </BriefingSection>
      <BriefingSection eyebrow="Services" title="Key services & deliverables">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <div className="miq-eyebrow mb-1">Key services</div>
            <BulletList items={o.key_services || []} />
          </div>
          <div>
            <div className="miq-eyebrow mb-1">Deliverables</div>
            <BulletList items={o.deliverables || []} />
          </div>
        </div>
      </BriefingSection>
      <BriefingSection eyebrow="Timeline" title="Period of performance">
        <p className="whitespace-pre-line">{o.timeline || "—"}</p>
      </BriefingSection>
      <BriefingSection eyebrow="Risks" title="Surfaced risks">
        <BulletList items={o.risks || []} />
      </BriefingSection>
      <BriefingSection eyebrow="Decision" title="Pursue / No-pursue indicators">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <div className="miq-eyebrow text-status-green mb-1">Pursue indicators</div>
            <BulletList items={o.pursue_indicators || []} />
          </div>
          <div>
            <div className="miq-eyebrow text-status-red mb-1">No-pursue indicators</div>
            <BulletList items={o.no_pursue_indicators || []} />
          </div>
        </div>
      </BriefingSection>
      <BriefingSection eyebrow="Findings" title="Key findings">
        <BulletList items={o.key_findings || []} />
      </BriefingSection>
      <BriefingSection eyebrow="Actions" title="Recommended actions">
        <ol className="list-decimal pl-5 space-y-1.5 text-[14px]">
          {(o.recommended_actions || []).map((a, i) => (
            <li key={i}>{a}</li>
          ))}
        </ol>
      </BriefingSection>
    </div>
  );
}

function Block({ label, body }: { label: string; body?: string }) {
  return (
    <div>
      <div className="miq-eyebrow mb-1">{label}</div>
      <p className="text-[14px] text-charcoal-900 whitespace-pre-wrap">{body || "—"}</p>
    </div>
  );
}

export default function SummaryPage({
  params,
}: {
  params: Promise<{ opportunityId: string }>;
}) {
  const { opportunityId } = use(params);
  return (
    <div>
      <PageHeader
        eyebrow="Capture Intelligence"
        title="Opportunity Summary"
        subtitle="Executive briefing derived from uploaded documents. Source-cited throughout."
      />
      <ModuleWorkbench
        opportunityId={opportunityId}
        moduleId="capture.opportunity_summary"
        moduleLabel="Opportunity Summary"
        description="Generate a mission-need, scope, deliverables, timeline, risks, and pursue/no-pursue briefing grounded in uploaded documents."
        renderer={renderSummary}
      />
    </div>
  );
}
