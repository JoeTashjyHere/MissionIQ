"use client";

import { use } from "react";
import { PageHeader } from "@/components/PageHeader";
import { ModuleWorkbench } from "@/components/intelligence/ModuleWorkbench";
import { BriefingSection } from "@/components/ds/BriefingSection";
import {
  ActionTracker,
  BasisLegend,
  ConfidenceGauge,
  DecisionCard,
  HistoricalEvidencePanel,
  InputsMissingBanner,
  PointList,
  RecommendationBanner,
  ScoreBar,
  StringList,
} from "@/components/briefings/Briefing";
import type { AIOutput, GateReviewOutput } from "@/lib/types";

const DECISION_LABEL: Record<string, string> = {
  pursue: "Pursue",
  pursue_with_conditions: "Pursue with Conditions",
  no_bid: "No-Bid",
};

function decisionTone(d: string): "green" | "amber" | "red" | "neutral" {
  if (d === "pursue") return "green";
  if (d === "pursue_with_conditions") return "amber";
  if (d === "no_bid") return "red";
  return "neutral";
}

function renderGateReview(output: AIOutput) {
  const o = output.output_json as unknown as GateReviewOutput;
  const pwin = o.probability_of_win;

  return (
    <div className="-mx-6">
      <div className="space-y-4 px-6 pb-5">
        {o.headline && (
          <p className="text-[16px] font-semibold leading-snug text-charcoal-900">
            {o.headline}
          </p>
        )}
        <RecommendationBanner
          eyebrow="Gate decision"
          decision={
            DECISION_LABEL[o.decision_recommendation] ??
            o.decision_recommendation
          }
          tone={decisionTone(o.decision_recommendation)}
          body={o.decision_summary}
          right={
            pwin && (
              <ConfidenceGauge
                score={pwin.score}
                level={pwin.level}
                label="Probability of win"
              />
            )
          }
        />
        <InputsMissingBanner missing={o.inputs_missing} />
        <BasisLegend />
      </div>

      <BriefingSection eyebrow="Scorecard" title="Gate review scores">
        <div className="grid gap-3 md:grid-cols-2">
          <ScoreBar label="Opportunity attractiveness" block={o.attractiveness_score} />
          <ScoreBar label="Competitive position" block={o.competitive_position_score} />
          <ScoreBar label="Capability alignment" block={o.capability_alignment_score} />
          <ScoreBar label="Risk (higher = more risk)" block={o.risk_score} invert />
        </div>
        {pwin?.rationale && (
          <p className="mt-3 text-[13px] text-charcoal-700">
            <span className="font-medium">Probability of win:</span>{" "}
            {pwin.rationale}
          </p>
        )}
      </BriefingSection>

      <BriefingSection eyebrow="The case" title="Reasons to pursue / not pursue">
        <div className="grid gap-4 md:grid-cols-2">
          <DecisionCard title="Top reasons to pursue">
            <PointList points={o.top_reasons_to_pursue} tone="positive" />
          </DecisionCard>
          <DecisionCard title="Top reasons not to pursue">
            <PointList points={o.top_reasons_not_to_pursue} tone="negative" />
          </DecisionCard>
        </div>
      </BriefingSection>

      <BriefingSection eyebrow="Action plan" title="Required executive actions">
        <ActionTracker actions={o.required_executive_actions} />
      </BriefingSection>

      <BriefingSection eyebrow="To resolve" title="Open questions & escalations">
        <div className="grid gap-4 md:grid-cols-2">
          <DecisionCard title="Open questions">
            <StringList items={o.open_questions} empty="None outstanding." />
          </DecisionCard>
          <DecisionCard title="Escalations">
            <StringList items={o.escalations} empty="None." />
          </DecisionCard>
        </div>
      </BriefingSection>

      <BriefingSection eyebrow="Institutional memory" title="Historical evidence">
        <HistoricalEvidencePanel evidence={o.historical_evidence} />
      </BriefingSection>

      {(o.key_findings?.length ?? 0) > 0 && (
        <BriefingSection eyebrow="Bottom line" title="Key findings">
          <StringList items={o.key_findings} />
        </BriefingSection>
      )}
    </div>
  );
}

export default function GateReviewPage({
  params,
}: {
  params: Promise<{ opportunityId: string }>;
}) {
  const { opportunityId } = use(params);
  return (
    <div>
      <PageHeader
        eyebrow="Briefings · Gate review package"
        title="Gate Review"
        subtitle={
          "A formal bid/no-bid gate-review package. MissionIQ scores opportunity " +
          "attractiveness, competitive position, capability alignment, and risk, " +
          "assesses probability of win, and lays out the reasons, actions, open " +
          "questions, and escalations a board needs to decide."
        }
      />
      <ModuleWorkbench
        opportunityId={opportunityId}
        moduleId="capture.gate_review"
        moduleLabel="Gate Review"
        description={
          "Generate a consulting-grade gate-review package. Requires a Customer " +
          "DNA Profile; runs sharpest after Win Strategy, Capability Match, and " +
          "Risk Intelligence are generated."
        }
        outputRenderer={renderGateReview}
      />
    </div>
  );
}
