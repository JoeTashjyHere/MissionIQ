"use client";

import { use } from "react";
import clsx from "clsx";
import { PageHeader } from "@/components/PageHeader";
import { ModuleWorkbench } from "@/components/intelligence/ModuleWorkbench";
import { BriefingSection, BulletList } from "@/components/ds/BriefingSection";
import { StatusPill } from "@/components/ds/StatusPill";
import type {
  AIOutput,
  EvaluationCriteriaOutput,
  EvaluationFactor,
} from "@/lib/types";

const IMPORTANCE_TONE: Record<
  EvaluationFactor["importance"],
  "red" | "amber" | "neutral" | "green"
> = {
  most_important: "red",
  important: "amber",
  less_important: "neutral",
  equal: "neutral",
  unspecified: "neutral",
};

function importanceLabel(i: EvaluationFactor["importance"]): string {
  return (
    {
      most_important: "Most important",
      important: "Important",
      less_important: "Less important",
      equal: "Equal",
      unspecified: "Unspecified",
    } as const
  )[i];
}

function renderEvaluation(output: AIOutput) {
  const o = output.output_json as unknown as EvaluationCriteriaOutput;

  return (
    <div className="-mx-6">
      <BriefingSection
        eyebrow="Executive summary"
        title="What the evaluation really tells us"
      >
        <p>{o.executive_summary || "—"}</p>
      </BriefingSection>

      <BriefingSection
        eyebrow="Section M decomposition"
        title={`Evaluation factors (${o.factors?.length ?? 0})`}
      >
        {(o.factors?.length ?? 0) === 0 ? (
          <p className="text-charcoal-500 italic text-[13px]">
            No factors extracted yet.
          </p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {(o.factors ?? []).map((f, i) => (
              <div
                key={i}
                className="rounded-md border border-charcoal-200 px-4 py-3"
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="font-semibold text-charcoal-900">
                      {f.factor}
                    </div>
                    {f.subfactor && (
                      <div className="text-[12.5px] text-charcoal-700">
                        {f.subfactor}
                      </div>
                    )}
                  </div>
                  <StatusPill tone={IMPORTANCE_TONE[f.importance]}>
                    {importanceLabel(f.importance)}
                  </StatusPill>
                </div>
                {(f.source_section || f.source_page) && (
                  <div className="mt-1 text-[11.5px] text-charcoal-500">
                    {f.source_section}
                    {f.source_page ? ` · p.${f.source_page}` : ""}
                  </div>
                )}
                {(f.required_response_elements?.length ?? 0) > 0 && (
                  <div className="mt-2">
                    <div className="miq-eyebrow">Required response elements</div>
                    <ul className="list-disc pl-5 text-[12.5px] space-y-1 mt-1">
                      {(f.required_response_elements ?? []).map((e, j) => (
                        <li key={j}>{e}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </BriefingSection>

      <BriefingSection
        eyebrow="Evaluation intelligence"
        title="How this acquisition will actually be decided"
        className="bg-deep-navy/3"
      >
        <p className="text-[14.5px] leading-relaxed">
          {o.evaluation_intelligence || "—"}
        </p>
      </BriefingSection>

      <div className="grid grid-cols-1 md:grid-cols-2">
        <BriefingSection
          eyebrow="Decision drivers"
          title="What will move the needle"
        >
          <BulletList items={o.likely_decision_drivers ?? []} />
        </BriefingSection>
        <BriefingSection
          eyebrow="Discriminators"
          title="Where a strong offeror can pull ahead"
        >
          <BulletList items={o.potential_discriminators ?? []} />
        </BriefingSection>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2">
        <BriefingSection
          eyebrow="Weaknesses"
          title="Likely weak spots"
          className={clsx("bg-status-redBg/40")}
        >
          <BulletList items={o.potential_weaknesses ?? []} />
        </BriefingSection>
        <BriefingSection
          eyebrow="Strategic recommendations"
          title="Capture moves to make"
        >
          <ol className="list-decimal pl-5 space-y-1.5 text-[14px]">
            {(o.strategic_recommendations ?? []).map((r, i) => (
              <li key={i}>{r}</li>
            ))}
          </ol>
        </BriefingSection>
      </div>

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

export default function EvaluationPage({
  params,
}: {
  params: Promise<{ opportunityId: string }>;
}) {
  const { opportunityId } = use(params);
  return (
    <div>
      <PageHeader
        eyebrow="Capture Intelligence"
        title="Evaluation Criteria"
        subtitle={
          "Section M decomposition PLUS evaluation intelligence: decision " +
          "drivers, discriminators, weaknesses, and strategic recommendations. " +
          "Shaped by the Customer DNA Profile."
        }
      />
      <ModuleWorkbench
        opportunityId={opportunityId}
        moduleId="capture.evaluation_criteria"
        moduleLabel="Evaluation Criteria"
        description={
          "Decompose Section M and produce capture-grade evaluation intelligence."
        }
        outputRenderer={renderEvaluation}
      />
    </div>
  );
}
