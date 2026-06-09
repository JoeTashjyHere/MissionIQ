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
  KpiBanner,
  PointList,
  RecommendationBanner,
  RiskHeatMap,
  StrengthWeaknessMatrix,
  StringList,
} from "@/components/briefings/Briefing";
import type { AIOutput, ExecRecommendationType, ExecutiveBriefOutput } from "@/lib/types";

const REC_LABEL: Record<ExecRecommendationType, string> = {
  pursue_aggressively: "Pursue Aggressively",
  pursue_with_conditions: "Pursue with Conditions",
  monitor: "Monitor",
  no_bid: "No-Bid",
};

function recTone(r: ExecRecommendationType): "green" | "amber" | "red" | "neutral" {
  if (r === "pursue_aggressively") return "green";
  if (r === "pursue_with_conditions") return "amber";
  if (r === "no_bid") return "red";
  return "neutral";
}

function renderExecutiveBrief(output: AIOutput) {
  const o = output.output_json as unknown as ExecutiveBriefOutput;
  const snap = o.opportunity_snapshot;
  const rec = o.executive_recommendation;

  return (
    <div className="-mx-6">
      <div className="space-y-4 px-6 pb-5">
        {o.headline && (
          <p className="text-[16px] font-semibold leading-snug text-charcoal-900">
            {o.headline}
          </p>
        )}
        <RecommendationBanner
          eyebrow="Executive recommendation"
          decision={REC_LABEL[rec.recommendation] ?? rec.recommendation}
          tone={recTone(rec.recommendation)}
          body={rec.rationale}
          right={
            <ConfidenceGauge
              score={rec.confidence_score}
              level={rec.confidence_level}
              label="Win confidence"
            />
          }
        />
        {rec.required_conditions?.length > 0 && (
          <DecisionCard eyebrow="Conditions" title="Required to proceed">
            <StringList items={rec.required_conditions} />
          </DecisionCard>
        )}
        <KpiBanner
          items={[
            { label: "Agency", value: snap.agency },
            { label: "Vehicle", value: snap.contract_vehicle },
            { label: "Est. Value", value: snap.estimated_value },
            { label: "Due", value: snap.due_date },
            { label: "Incumbent", value: snap.incumbent },
            { label: "Program", value: snap.program },
            { label: "Status", value: snap.pursuit_status },
            {
              label: "Win Confidence",
              value: `${snap.win_confidence}%`,
              tone:
                snap.win_confidence >= 60
                  ? "green"
                  : snap.win_confidence >= 40
                    ? "amber"
                    : "red",
            },
          ]}
        />
        <InputsMissingBanner missing={o.inputs_missing} />
        <BasisLegend />
      </div>

      <BriefingSection eyebrow="Section 2" title="Customer intelligence">
        <div className="grid gap-4 md:grid-cols-2">
          <DecisionCard title="Strategic priorities">
            <StringList items={o.customer_intelligence.strategic_priorities} />
          </DecisionCard>
          <DecisionCard title="Success metrics">
            <StringList items={o.customer_intelligence.success_metrics} />
          </DecisionCard>
          <DecisionCard title="Stakeholder concerns">
            <StringList items={o.customer_intelligence.stakeholder_concerns} />
          </DecisionCard>
          <DecisionCard title="Mission drivers">
            <StringList items={o.customer_intelligence.mission_drivers} />
          </DecisionCard>
        </div>
      </BriefingSection>

      <BriefingSection eyebrow="Section 3" title="Company position">
        <StrengthWeaknessMatrix
          leftLabel="Strengths"
          rightLabel="Gaps"
          left={o.company_position.strengths}
          right={o.company_position.gaps}
        />
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <DecisionCard title="Proof points">
            <PointList points={o.company_position.proof_points} />
          </DecisionCard>
          <DecisionCard title="Competitive advantages">
            <PointList points={o.company_position.competitive_advantages} />
          </DecisionCard>
        </div>
      </BriefingSection>

      <BriefingSection eyebrow="Section 4" title="Win strategy">
        <div className="grid gap-4 md:grid-cols-2">
          <DecisionCard title="Recommended discriminators">
            <PointList points={o.win_strategy.recommended_discriminators} />
          </DecisionCard>
          <DecisionCard title="Key themes">
            <PointList points={o.win_strategy.key_themes} />
          </DecisionCard>
          <DecisionCard title="Evaluation priorities">
            <PointList points={o.win_strategy.evaluation_priorities} />
          </DecisionCard>
          <DecisionCard title="Critical actions">
            <ActionTracker actions={o.win_strategy.critical_actions} />
          </DecisionCard>
        </div>
      </BriefingSection>

      <BriefingSection eyebrow="Section 5" title="Risks">
        <RiskHeatMap
          groups={[
            { label: "Capture", risks: o.risks.top_capture_risks },
            { label: "Proposal", risks: o.risks.top_proposal_risks },
            { label: "Delivery", risks: o.risks.top_delivery_risks },
          ]}
        />
      </BriefingSection>

      <BriefingSection
        eyebrow="Institutional memory"
        title="Historical evidence"
      >
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

export default function ExecutiveBriefPage({
  params,
}: {
  params: Promise<{ opportunityId: string }>;
}) {
  const { opportunityId } = use(params);
  return (
    <div>
      <PageHeader
        eyebrow="Briefings · Leadership deliverable"
        title="Executive Brief"
        subtitle={
          "A one-screen, boardroom-ready brief. MissionIQ synthesizes Customer " +
          "DNA, Company DNA, Capability Match, Evaluation and Risk Intelligence, " +
          "Win Strategy, market intelligence, and Pursuit Memory into a single " +
          "leadership decision — what's happening, why it matters, and what to do."
        }
      />
      <ModuleWorkbench
        opportunityId={opportunityId}
        moduleId="capture.executive_brief"
        moduleLabel="Executive Brief"
        description={
          "Generate a leadership-quality executive brief. Requires a Customer " +
          "DNA Profile; for the sharpest brief, run Win Strategy and the upstream " +
          "modules first — the brief reads them all and dampens confidence when " +
          "inputs are missing."
        }
        outputRenderer={renderExecutiveBrief}
      />
    </div>
  );
}
