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
  RecommendationBanner,
  ScoreBar,
  StringList,
} from "@/components/briefings/Briefing";
import type { AIOutput, BidDecisionOutput, ScoreBlock } from "@/lib/types";

const REC_LABEL: Record<string, string> = {
  bid: "Bid",
  conditional_bid: "Conditional Bid",
  no_bid: "No-Bid",
};

function recTone(r: string): "green" | "amber" | "red" | "neutral" {
  if (r === "bid") return "green";
  if (r === "conditional_bid") return "amber";
  if (r === "no_bid") return "red";
  return "neutral";
}

function renderBidDecision(output: AIOutput) {
  const o = output.output_json as unknown as BidDecisionOutput;
  const conf = o.confidence;

  return (
    <div className="-mx-6">
      <div className="space-y-4 px-6 pb-5">
        <RecommendationBanner
          eyebrow="Bid / No-Bid recommendation"
          decision={REC_LABEL[o.recommendation] ?? o.recommendation}
          tone={recTone(o.recommendation)}
          body={o.executive_summary}
          right={
            conf && (
              <ConfidenceGauge
                score={conf.score}
                level={conf.level}
                label="Decision confidence"
              />
            )
          }
        />
        {conf?.rationale && (
          <p className="text-[13px] text-charcoal-700">
            <span className="font-medium">Confidence rationale:</span>{" "}
            {conf.rationale}
          </p>
        )}
        <InputsMissingBanner missing={o.inputs_missing} />
        <BasisLegend />
      </div>

      <BriefingSection
        eyebrow="Decision factors"
        title="Scored across the six factors"
      >
        <div className="grid gap-3 md:grid-cols-2">
          {o.factors.map((f, i) => {
            const block: ScoreBlock = {
              score: f.score,
              rationale: f.rationale,
              basis: f.basis,
              drivers: [],
              sources: f.evidence,
            };
            return (
              <ScoreBar
                key={i}
                label={`${f.name} · ${f.confidence} confidence`}
                block={block}
              />
            );
          })}
        </div>
      </BriefingSection>

      <BriefingSection eyebrow="What drives it" title="Decision drivers">
        <StringList items={o.decision_drivers} />
      </BriefingSection>

      <BriefingSection eyebrow="Action plan" title="Required next steps">
        <ActionTracker actions={o.required_next_steps} />
      </BriefingSection>

      <BriefingSection eyebrow="Institutional memory" title="Historical evidence">
        <HistoricalEvidencePanel evidence={o.historical_evidence} />
      </BriefingSection>
    </div>
  );
}

export default function BidDecisionPage({
  params,
}: {
  params: Promise<{ opportunityId: string }>;
}) {
  const { opportunityId } = use(params);
  return (
    <div>
      <PageHeader
        eyebrow="Briefings · Executive decision"
        title="Bid / No-Bid Decision"
        subtitle={
          "A focused executive recommendation. MissionIQ scores the six decision " +
          "factors — Strategic Alignment, Revenue Potential, Relationship " +
          "Position, Competitive Position, Delivery Readiness, and Risk Profile — " +
          "and returns Bid, Conditional Bid, or No-Bid with the drivers and next " +
          "steps."
        }
      />
      <ModuleWorkbench
        opportunityId={opportunityId}
        moduleId="capture.bid_decision"
        moduleLabel="Bid / No-Bid Decision"
        description={
          "Generate a focused bid/no-bid recommendation. Requires a Customer DNA " +
          "Profile; sharpest after Win Strategy, Capability Match, and Risk " +
          "Intelligence are generated."
        }
        outputRenderer={renderBidDecision}
      />
    </div>
  );
}
