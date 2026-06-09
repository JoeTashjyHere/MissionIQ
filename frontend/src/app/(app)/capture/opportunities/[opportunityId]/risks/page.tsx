"use client";

import { use } from "react";
import clsx from "clsx";
import { PageHeader } from "@/components/PageHeader";
import { ModuleWorkbench } from "@/components/intelligence/ModuleWorkbench";
import { BriefingSection, BulletList } from "@/components/ds/BriefingSection";
import { StatusPill } from "@/components/ds/StatusPill";
import type { AIOutput, RiskItem, RiskRegisterOutput } from "@/lib/types";

const SEVERITY_TONE: Record<
  RiskItem["severity"],
  "red" | "amber" | "neutral" | "green"
> = {
  critical: "red",
  high: "red",
  medium: "amber",
  low: "neutral",
};

const PROBABILITY_TONE: Record<
  RiskItem["probability"],
  "red" | "amber" | "neutral" | "green"
> = {
  high: "red",
  medium: "amber",
  low: "neutral",
};

const LANE_DEFS: Array<{
  key: keyof RiskRegisterOutput;
  label: string;
  eyebrow: string;
  description: string;
}> = [
  {
    key: "capture_risks",
    label: "Capture risks",
    eyebrow: "Lane · Win",
    description: "Things that threaten winning the bid.",
  },
  {
    key: "proposal_risks",
    label: "Proposal risks",
    eyebrow: "Lane · Write",
    description:
      "Things that threaten producing a compliant, compelling proposal on time.",
  },
  {
    key: "delivery_risks",
    label: "Delivery risks",
    eyebrow: "Lane · Execute",
    description: "Things that threaten executing the contract after award.",
  },
  {
    key: "customer_risks",
    label: "Customer risks",
    eyebrow: "Lane · Mission",
    description:
      "Things that affect the customer's mission or reputation if we win or lose.",
  },
];

function RiskCard({ risk }: { risk: RiskItem }) {
  return (
    <div className="rounded-md border border-charcoal-200 px-4 py-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="font-semibold text-charcoal-900">{risk.title}</div>
          {risk.owner && (
            <div className="text-[11.5px] text-charcoal-500 mt-0.5">
              Owner: {risk.owner}
            </div>
          )}
        </div>
        <div className="flex flex-col items-end gap-1 shrink-0">
          <StatusPill tone={SEVERITY_TONE[risk.severity]}>
            Severity: {risk.severity}
          </StatusPill>
          <StatusPill tone={PROBABILITY_TONE[risk.probability]}>
            Probability: {risk.probability}
          </StatusPill>
        </div>
      </div>
      <p className="mt-2 text-[13.5px] text-charcoal-900">{risk.description}</p>
      <div className="mt-2">
        <div className="miq-eyebrow">Mission impact</div>
        <p className="text-[13px] text-charcoal-700">{risk.mission_impact}</p>
      </div>
      <div className="mt-2">
        <div className="miq-eyebrow">Mitigation</div>
        <p className="text-[13px] text-charcoal-700">{risk.mitigation}</p>
      </div>
      {(risk.supporting_evidence?.length ?? 0) > 0 && (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {(risk.supporting_evidence ?? []).map((ref, i) => (
            <span
              key={i}
              className="inline-flex items-center rounded border border-charcoal-200 px-1.5 py-0.5 text-[11px] font-mono text-charcoal-700"
            >
              {ref}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

function renderRisks(output: AIOutput) {
  const o = output.output_json as unknown as RiskRegisterOutput;
  const totalRisks =
    (o.capture_risks?.length ?? 0) +
    (o.proposal_risks?.length ?? 0) +
    (o.delivery_risks?.length ?? 0) +
    (o.customer_risks?.length ?? 0);

  return (
    <div className="-mx-6">
      <BriefingSection
        eyebrow="Executive summary"
        title="The risk story at a portfolio level"
      >
        <p>{o.executive_summary || "—"}</p>
        <div className="mt-3 text-[12.5px] text-charcoal-500">
          {totalRisks} risk{totalRisks === 1 ? "" : "s"} across 4 lanes
        </div>
      </BriefingSection>

      {(o.top_risks?.length ?? 0) > 0 && (
        <BriefingSection
          eyebrow="Top risks"
          title="The 3–5 most material risks across all lanes"
          className="bg-status-redBg/40"
        >
          <BulletList items={o.top_risks ?? []} />
        </BriefingSection>
      )}

      {LANE_DEFS.map((lane) => {
        const items = (o[lane.key] as RiskItem[] | undefined) ?? [];
        return (
          <BriefingSection
            key={lane.key}
            eyebrow={lane.eyebrow}
            title={`${lane.label} (${items.length})`}
            className={clsx(items.length === 0 && "opacity-80")}
          >
            <p className="text-[12.5px] text-charcoal-500 mb-3">
              {lane.description}
            </p>
            {items.length === 0 ? (
              <p className="text-charcoal-500 italic text-[13px]">
                No risks identified in this lane.
              </p>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {items.map((r, i) => (
                  <RiskCard key={i} risk={r} />
                ))}
              </div>
            )}
          </BriefingSection>
        );
      })}

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

export default function RisksPage({
  params,
}: {
  params: Promise<{ opportunityId: string }>;
}) {
  const { opportunityId } = use(params);
  return (
    <div>
      <PageHeader
        eyebrow="Capture Intelligence"
        title="Risk Register"
        subtitle={
          "Categorized risks across Capture, Proposal, Delivery, and Customer " +
          "lanes. Every risk carries mission impact, probability, severity, " +
          "mitigation, and supporting evidence — weighted against the " +
          "Customer DNA Profile."
        }
      />
      <ModuleWorkbench
        opportunityId={opportunityId}
        moduleId="capture.risk_register"
        moduleLabel="Risk Register"
        description={
          "Identify risks across Capture, Proposal, Delivery, and Customer " +
          "lanes. Each risk is sized by mission impact, not contract value."
        }
        outputRenderer={renderRisks}
      />
    </div>
  );
}
