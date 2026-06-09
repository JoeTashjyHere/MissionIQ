"use client";

import { use } from "react";
import { PageHeader } from "@/components/PageHeader";
import { ModuleWorkbench } from "@/components/intelligence/ModuleWorkbench";
import { BriefingSection } from "@/components/ds/BriefingSection";
import { StatusPill } from "@/components/ds/StatusPill";
import type {
  AIOutput,
  BlackHatPoint,
  CaptureAction,
  CompetitorPosture,
  StrategicBasis,
  StrategicPoint,
  WinStrategyOutput,
} from "@/lib/types";

const PURSUIT_LABEL: Record<string, string> = {
  pursue: "Pursue",
  pursue_with_conditions: "Pursue with Conditions",
  no_bid: "No-Bid",
};

function pursuitTone(p?: string): "green" | "amber" | "red" | "neutral" {
  if (p === "pursue") return "green";
  if (p === "pursue_with_conditions") return "amber";
  if (p === "no_bid") return "red";
  return "neutral";
}

function confTone(l?: string): "green" | "amber" | "red" | "neutral" {
  if (l === "high") return "green";
  if (l === "medium") return "amber";
  if (l === "low") return "red";
  return "neutral";
}

const BASIS_STYLE: Record<StrategicBasis, { label: string; cls: string }> = {
  evidence: {
    label: "Evidence",
    cls: "bg-status-greenBg text-status-green",
  },
  inference: {
    label: "Inference",
    cls: "bg-steel-700/10 text-steel-700",
  },
  assumption: {
    label: "Assumption",
    cls: "bg-status-amberBg text-status-amber",
  },
};

function BasisChip({ basis }: { basis?: StrategicBasis }) {
  const s = BASIS_STYLE[basis ?? "inference"];
  return (
    <span
      className={`inline-flex items-center rounded px-1.5 py-0.5 text-[10.5px] font-semibold uppercase tracking-wide ${s.cls}`}
    >
      {s.label}
    </span>
  );
}

function Sources({ sources }: { sources?: string[] }) {
  if (!sources?.length) return null;
  return (
    <div className="mt-1 flex flex-wrap gap-1">
      {sources.map((s, i) => (
        <span
          key={i}
          className="rounded bg-charcoal-100 px-1.5 py-0.5 text-[10.5px] font-mono text-charcoal-600"
        >
          {s}
        </span>
      ))}
    </div>
  );
}

function PointList({ points }: { points?: StrategicPoint[] }) {
  if (!points?.length) {
    return <p className="text-charcoal-500 italic text-[13px]">None identified.</p>;
  }
  return (
    <ul className="flex flex-col gap-2.5">
      {points.map((p, i) => (
        <li
          key={i}
          className="rounded-md border border-charcoal-200 px-3 py-2.5"
        >
          <div className="flex items-start justify-between gap-3">
            <p className="text-[14px] text-charcoal-900 leading-relaxed">
              {p.statement}
            </p>
            <BasisChip basis={p.basis} />
          </div>
          <Sources sources={p.sources} />
        </li>
      ))}
    </ul>
  );
}

function BasisLegend() {
  return (
    <div className="flex flex-wrap items-center gap-3 text-[12px] text-charcoal-600">
      <span className="font-medium text-charcoal-700">How to read this:</span>
      <span className="inline-flex items-center gap-1.5">
        <BasisChip basis="evidence" /> backed by a cited input
      </span>
      <span className="inline-flex items-center gap-1.5">
        <BasisChip basis="inference" /> professional judgment from the inputs
      </span>
      <span className="inline-flex items-center gap-1.5">
        <BasisChip basis="assumption" /> belief to validate before bid
      </span>
    </div>
  );
}

function ConfidenceGauge({ score, level }: { score: number; level?: string }) {
  const pct = Math.max(0, Math.min(100, score));
  const barColor =
    level === "high"
      ? "bg-status-green"
      : level === "low"
        ? "bg-status-red"
        : "bg-status-amber";
  return (
    <div className="w-full sm:w-64">
      <div className="flex items-baseline justify-between">
        <span className="miq-eyebrow">Win confidence</span>
        <span className="miq-numeric text-[26px] font-semibold leading-none text-charcoal-900">
          {pct}
          <span className="text-[14px] text-charcoal-500">%</span>
        </span>
      </div>
      <div className="mt-2 h-2 w-full rounded-full bg-charcoal-100">
        <div
          className={`h-2 rounded-full ${barColor}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

const PRIORITY_LABEL: Record<string, string> = {
  immediate: "Immediate",
  near_term: "Near-term",
  pre_rfp: "Pre-RFP",
};

function priorityTone(p?: string): "red" | "amber" | "neutral" {
  if (p === "immediate") return "red";
  if (p === "near_term") return "amber";
  return "neutral";
}

function threatTone(t?: string): "green" | "amber" | "red" | "neutral" {
  if (t === "low") return "green";
  if (t === "medium") return "amber";
  if (t === "high") return "red";
  return "neutral";
}

function renderWinStrategy(output: AIOutput) {
  const o = output.output_json as unknown as WinStrategyOutput;
  const conf = o.win_confidence_assessment;

  return (
    <div className="-mx-6">
      {/* Executive recommendation hero */}
      <div className="px-6 pb-5">
        <div className="rounded-lg border border-charcoal-200 bg-gradient-to-br from-steel-700/[0.06] to-transparent p-5">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div className="flex-1">
              <div className="miq-eyebrow">Executive pursuit recommendation</div>
              <div className="mt-1.5 flex items-center gap-2">
                <StatusPill tone={pursuitTone(o.pursuit_recommendation)}>
                  {PURSUIT_LABEL[o.pursuit_recommendation] ??
                    o.pursuit_recommendation}
                </StatusPill>
                {conf && (
                  <StatusPill tone={confTone(conf.level)}>
                    {conf.level} confidence
                  </StatusPill>
                )}
              </div>
              <p className="mt-3 text-[15px] leading-relaxed text-charcoal-900 max-w-3xl">
                {o.executive_pursuit_recommendation || "—"}
              </p>
            </div>
            {conf && (
              <ConfidenceGauge score={conf.score} level={conf.level} />
            )}
          </div>
          {(o.inputs_missing?.length ?? 0) > 0 && (
            <div className="mt-4 rounded-md bg-status-amberBg border border-status-amber/30 px-3 py-2 text-[12.5px] text-charcoal-800">
              <span className="font-semibold">
                Synthesis run with partial inputs.
              </span>{" "}
              Missing: {(o.inputs_missing ?? []).join(", ")}. Generate these
              upstream modules and regenerate for a higher-confidence assessment.
            </div>
          )}
          <div className="mt-4">
            <BasisLegend />
          </div>
        </div>
      </div>

      <BriefingSection eyebrow="Position" title="Strengths">
        <PointList points={o.strengths} />
      </BriefingSection>

      <BriefingSection eyebrow="Exposure" title="Weaknesses">
        <PointList points={o.weaknesses} />
      </BriefingSection>

      <BriefingSection eyebrow="Edge" title="Key discriminators">
        <PointList points={o.key_discriminators} />
      </BriefingSection>

      <BriefingSection
        eyebrow="Black hat"
        title="How a competitor attacks us — and our counter"
      >
        {(o.black_hat_assessment?.length ?? 0) === 0 ? (
          <p className="text-charcoal-500 italic text-[13px]">None identified.</p>
        ) : (
          <ul className="flex flex-col gap-3">
            {(o.black_hat_assessment ?? []).map((b: BlackHatPoint, i) => (
              <li
                key={i}
                className="rounded-md border border-status-red/20 bg-status-redBg/40 px-3 py-2.5"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="font-semibold text-[14px] text-charcoal-900">
                    {b.competitor_move}
                  </div>
                  <BasisChip basis={b.basis} />
                </div>
                <p className="mt-1 text-[13px] text-charcoal-700">
                  <span className="font-medium">Impact:</span> {b.impact}
                </p>
                <p className="mt-1 text-[13px] text-charcoal-900">
                  <span className="font-medium">Our counter:</span>{" "}
                  {b.our_counter}
                </p>
                <Sources sources={b.sources} />
              </li>
            ))}
          </ul>
        )}
      </BriefingSection>

      <BriefingSection
        eyebrow="Evaluator lens"
        title="Likely evaluator concerns about us"
      >
        <PointList points={o.likely_evaluator_concerns} />
      </BriefingSection>

      <BriefingSection eyebrow="Messaging" title="Win themes">
        <PointList points={o.win_themes} />
      </BriefingSection>

      <BriefingSection eyebrow="Field" title="Competitive assessment">
        <p className="text-[14px] text-charcoal-900 leading-relaxed">
          {o.competitive_assessment?.summary || "—"}
        </p>
        <div className="mt-3 flex flex-col gap-2">
          {(o.competitive_assessment?.competitors ?? []).map(
            (c: CompetitorPosture, i) => (
              <div
                key={i}
                className="rounded-md border border-charcoal-200 px-3 py-2.5"
              >
                <div className="flex items-center justify-between gap-3">
                  <div className="font-semibold text-[14px] text-charcoal-900">
                    {c.name}
                  </div>
                  <div className="flex items-center gap-2">
                    <StatusPill tone={threatTone(c.threat_level)}>
                      {c.threat_level} threat
                    </StatusPill>
                    <BasisChip basis={c.basis} />
                  </div>
                </div>
                <p className="mt-1 text-[13px] text-charcoal-700">
                  {c.positioning}
                </p>
                <p className="mt-1 text-[13px] text-charcoal-900">
                  <span className="font-medium">Our response:</span>{" "}
                  {c.our_response}
                </p>
                <Sources sources={c.sources} />
              </div>
            ),
          )}
        </div>
      </BriefingSection>

      <BriefingSection
        eyebrow="Action plan"
        title="Critical capture actions"
      >
        {(o.critical_capture_actions?.length ?? 0) === 0 ? (
          <p className="text-charcoal-500 italic text-[13px]">None identified.</p>
        ) : (
          <ol className="flex flex-col gap-2">
            {(o.critical_capture_actions ?? []).map((a: CaptureAction, i) => (
              <li
                key={i}
                className="flex items-start gap-3 rounded-md border border-charcoal-200 px-3 py-2.5"
              >
                <StatusPill tone={priorityTone(a.priority)}>
                  {PRIORITY_LABEL[a.priority] ?? a.priority}
                </StatusPill>
                <div className="flex-1">
                  <div className="font-medium text-[14px] text-charcoal-900">
                    {a.action}
                  </div>
                  <p className="mt-0.5 text-[13px] text-charcoal-700">
                    {a.rationale}
                  </p>
                  {a.owner && (
                    <div className="mt-0.5 text-[11.5px] text-charcoal-500">
                      Owner: {a.owner}
                    </div>
                  )}
                </div>
              </li>
            ))}
          </ol>
        )}
      </BriefingSection>

      {conf && (
        <BriefingSection
          eyebrow="Verdict"
          title="Win confidence assessment"
        >
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <ConfidenceGauge score={conf.score} level={conf.level} />
            <p className="flex-1 text-[14px] text-charcoal-900 leading-relaxed">
              {conf.rationale}
            </p>
          </div>
          {(conf.key_drivers?.length ?? 0) > 0 && (
            <ul className="mt-3 list-disc pl-5 space-y-1 text-[13px]">
              {(conf.key_drivers ?? []).map((d, i) => (
                <li key={i}>{d}</li>
              ))}
            </ul>
          )}
        </BriefingSection>
      )}
    </div>
  );
}

export default function WinStrategyPage({
  params,
}: {
  params: Promise<{ opportunityId: string }>;
}) {
  const { opportunityId } = use(params);
  return (
    <div>
      <PageHeader
        eyebrow="Capture Intelligence · Flagship deliverable"
        title="Win Strategy"
        subtitle={
          "The gate-review assessment. MissionIQ synthesizes Customer DNA, " +
          "Company DNA, opportunity documents, evaluation criteria, Capability " +
          "Match, market intelligence, and the Risk Register into a senior-" +
          "capture-executive win strategy — strategic recommendations, not a " +
          "document summary. Every point is tagged Evidence, Inference, or " +
          "Assumption and cites its sources."
        }
      />
      <ModuleWorkbench
        opportunityId={opportunityId}
        moduleId="capture.win_strategy"
        moduleLabel="Win Strategy"
        description={
          "Synthesize the full pursuit picture into a gate-review win strategy. " +
          "Requires a Customer DNA Profile. For the sharpest, highest-confidence " +
          "assessment, generate Company DNA, Capability Match, Evaluation " +
          "Criteria, and the Risk Register first — Win Strategy reads them all."
        }
        outputRenderer={renderWinStrategy}
      />
    </div>
  );
}
