"use client";

import { use } from "react";
import { PageHeader } from "@/components/PageHeader";
import { ModuleWorkbench } from "@/components/intelligence/ModuleWorkbench";
import { BriefingSection } from "@/components/ds/BriefingSection";
import {
  ActionTracker,
  BasisLegend,
  ConfidenceGauge,
  HistoricalEvidencePanel,
  InputsMissingBanner,
  PointList,
  RecommendationBanner,
} from "@/components/briefings/Briefing";
import type { AIOutput, OutcomeIntelligenceOutput } from "@/lib/types";

function renderOutcomeIntelligence(output: AIOutput) {
  const o = output.output_json as unknown as OutcomeIntelligenceOutput;
  const conf = o.confidence;

  return (
    <div className="-mx-6">
      <div className="space-y-4 px-6 pb-5">
        <RecommendationBanner
          eyebrow="What our track record means here"
          decision="Outcome Intelligence"
          tone="neutral"
          body={o.outcome_context_summary}
          right={
            conf && (
              <ConfidenceGauge
                score={conf.score}
                level={conf.level}
                label="Analysis confidence"
              />
            )
          }
        />
        <p className="text-[12px] text-charcoal-500">
          Track records below are observed patterns and historical correlations
          with supporting evidence — MissionIQ never claims a pattern caused a
          win or loss.
        </p>
        <InputsMissingBanner missing={o.inputs_missing} />
        <BasisLegend />
      </div>

      <BriefingSection
        eyebrow="Observed patterns"
        title="Win patterns relevant to this pursuit"
      >
        <PointList
          points={o.relevant_win_patterns}
          tone="positive"
          empty="No relevant win patterns observed yet — record outcomes as pursuits close."
        />
      </BriefingSection>

      <BriefingSection
        eyebrow="Historical correlations"
        title="Loss patterns to pre-empt"
      >
        <PointList
          points={o.relevant_loss_patterns}
          tone="negative"
          empty="No relevant loss patterns observed yet."
        />
      </BriefingSection>

      <BriefingSection eyebrow="Agency" title="Agency track record">
        <PointList
          points={o.agency_track_record}
          empty="No decided pursuits recorded at this agency yet."
        />
      </BriefingSection>

      <BriefingSection eyebrow="Competition" title="Competitor track record">
        <PointList
          points={o.competitor_track_record}
          empty="No competitor outcome history recorded yet."
        />
      </BriefingSection>

      <BriefingSection eyebrow="Action plan" title="Strategic recommendations">
        <ActionTracker actions={o.strategic_recommendations} />
      </BriefingSection>

      <BriefingSection eyebrow="Institutional memory" title="Historical evidence">
        <HistoricalEvidencePanel evidence={o.historical_evidence} />
      </BriefingSection>
    </div>
  );
}

export default function OutcomeIntelPage({
  params,
}: {
  params: Promise<{ opportunityId: string }>;
}) {
  const { opportunityId } = use(params);
  return (
    <div>
      <PageHeader
        eyebrow="Memory · Closed-loop learning"
        title="Outcome Intelligence"
        subtitle={
          "What the organization's recorded win/loss history means for this " +
          "pursuit: relevant win patterns, recurring loss patterns, agency and " +
          "competitor track records, and the strategic moves they imply. " +
          "Patterns are observed correlations — never causal claims."
        }
      />
      <ModuleWorkbench
        opportunityId={opportunityId}
        moduleId="capture.outcome_intelligence"
        moduleLabel="Outcome Intelligence"
        description={
          "Apply the organization's recorded pursuit outcomes to this " +
          "opportunity. Sharpest once outcomes have been recorded for completed " +
          "pursuits — record them from each pursuit's briefing page."
        }
        outputRenderer={renderOutcomeIntelligence}
      />
    </div>
  );
}
