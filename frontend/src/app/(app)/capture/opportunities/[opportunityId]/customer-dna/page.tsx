"use client";

import { use } from "react";
import { PageHeader } from "@/components/PageHeader";
import { ModuleWorkbench } from "@/components/intelligence/ModuleWorkbench";
import { BriefingSection, BulletList } from "@/components/ds/BriefingSection";
import { StatusPill } from "@/components/ds/StatusPill";
import type { AIOutput, CustomerDnaProfile } from "@/lib/types";

function confidenceTone(c?: string): "green" | "amber" | "red" | "neutral" {
  if (c === "high") return "green";
  if (c === "medium") return "amber";
  if (c === "low" || c === "insufficient") return "red";
  return "neutral";
}

function renderDna(output: AIOutput) {
  const o = output.output_json as unknown as CustomerDnaProfile & {
    _notice?: string;
  };

  return (
    <div className="-mx-6">
      {o._notice && (
        <div className="mx-6 mb-3 rounded-md bg-steel-700/10 text-steel-700 text-[12px] px-3 py-2">
          {o._notice}
        </div>
      )}

      <BriefingSection eyebrow="Identity" title="Who this customer is">
        <div className="flex items-start gap-3">
          <div className="flex-1">
            <p className="text-[15px] leading-relaxed whitespace-pre-line">
              {o.mission || "—"}
            </p>
            <p className="mt-3 text-[14px] text-charcoal-700 leading-relaxed">
              {o.executive_summary || "—"}
            </p>
          </div>
          <StatusPill tone={confidenceTone(o.confidence)}>
            {o.confidence ? `Confidence: ${o.confidence}` : "Confidence: —"}
          </StatusPill>
        </div>
      </BriefingSection>

      <BriefingSection eyebrow="Strategy" title="What they are pursuing">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Column label="Strategic goals" items={o.strategic_goals} />
          <Column label="Success metrics" items={o.success_metrics} />
        </div>
      </BriefingSection>

      <BriefingSection eyebrow="Culture" title="How they decide">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Column label="Core values" items={o.core_values} />
          <Column label="Stakeholder concerns" items={o.stakeholder_concerns} />
        </div>
      </BriefingSection>

      <BriefingSection eyebrow="Operations" title="What is on their plate">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Column
            label="Operational challenges"
            items={o.operational_challenges}
          />
          <Column
            label="Technology priorities"
            items={o.technology_priorities}
          />
        </div>
      </BriefingSection>

      <BriefingSection
        eyebrow="Risk posture"
        title="What they are actively trying to avoid"
      >
        <Column label="Risk priorities" items={o.risk_priorities} />
      </BriefingSection>

      {(o.key_findings?.length ?? 0) > 0 && (
        <BriefingSection eyebrow="Findings" title="Key analyst findings">
          <BulletList items={o.key_findings ?? []} />
        </BriefingSection>
      )}

      {(o.recommended_actions?.length ?? 0) > 0 && (
        <BriefingSection
          eyebrow="Next moves"
          title="Recommended actions for the capture team"
        >
          <ol className="list-decimal pl-5 space-y-1.5 text-[14px]">
            {(o.recommended_actions ?? []).map((a, i) => (
              <li key={i}>{a}</li>
            ))}
          </ol>
        </BriefingSection>
      )}
    </div>
  );
}

function Column({ label, items }: { label: string; items?: string[] }) {
  return (
    <div>
      <div className="miq-eyebrow mb-1">{label}</div>
      <BulletList items={items ?? []} />
    </div>
  );
}

export default function CustomerDnaPage({
  params,
}: {
  params: Promise<{ opportunityId: string }>;
}) {
  const { opportunityId } = use(params);
  return (
    <div>
      <PageHeader
        eyebrow="Capture Intelligence · Synthesis"
        title="Customer DNA Profile"
        subtitle={
          "The portrait of the customer behind this opportunity. MissionIQ " +
          "synthesizes their mission, strategic goals, values, success metrics, " +
          "operational challenges, technology priorities, risk priorities, and " +
          "stakeholder concerns from your evidence. Every downstream Capture " +
          "module — Compliance Matrix, Evaluation Criteria, Risk Register — " +
          "consumes this profile so its output is shaped by the customer, " +
          "not by generic AI extraction."
        }
      />
      <ModuleWorkbench
        opportunityId={opportunityId}
        moduleId="capture.customer_dna"
        moduleLabel="Customer DNA Profile"
        description={
          "Synthesize a Customer DNA Profile from uploaded documents and " +
          "linked market intelligence. Generate this BEFORE the consultant-" +
          "grade modules (Compliance, Evaluation, Risks) — they read this " +
          "profile to produce mission-aligned output."
        }
        outputRenderer={renderDna}
      />
    </div>
  );
}
