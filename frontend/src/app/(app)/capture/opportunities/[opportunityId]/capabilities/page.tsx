"use client";

import { use } from "react";
import Link from "next/link";
import { PageHeader } from "@/components/PageHeader";
import { ModuleWorkbench } from "@/components/intelligence/ModuleWorkbench";
import { BriefingSection, BulletList } from "@/components/ds/BriefingSection";
import { StatusPill } from "@/components/ds/StatusPill";
import type {
  AIOutput,
  CapabilityMatchOutput,
  CompanyGapRisk,
  FitArea,
  TeamingRecommendation,
} from "@/lib/types";

function fitTone(s?: string): "green" | "amber" | "red" | "neutral" {
  if (s === "strong") return "green";
  if (s === "moderate") return "amber";
  if (s === "marginal" || s === "weak") return "red";
  return "neutral";
}

function severityTone(s?: string): "green" | "amber" | "red" | "neutral" {
  if (s === "low") return "green";
  if (s === "medium") return "amber";
  if (s === "high" || s === "critical") return "red";
  return "neutral";
}

function FitCard({ fit, tone }: { fit: FitArea; tone: "green" | "red" }) {
  return (
    <div
      className={
        "rounded-md border px-3 py-2.5 " +
        (tone === "green"
          ? "border-status-green/30 bg-status-greenBg"
          : "border-status-red/30 bg-status-redBg")
      }
    >
      <div className="flex items-center justify-between gap-2">
        <div className="font-semibold text-[14px] text-charcoal-900">
          {fit.area}
        </div>
        {fit.confidence && (
          <StatusPill tone="neutral">conf: {fit.confidence}</StatusPill>
        )}
      </div>
      <p className="mt-1 text-[13px] text-charcoal-700 leading-relaxed">
        {fit.rationale}
      </p>
      {(fit.evidence_refs?.length ?? 0) > 0 && (
        <div className="mt-1.5 text-[11px] text-charcoal-500">
          Evidence: {(fit.evidence_refs ?? []).join(", ")}
        </div>
      )}
    </div>
  );
}

function renderMatch(output: AIOutput) {
  const o = output.output_json as unknown as CapabilityMatchOutput;

    return (
      <div className="-mx-6">
        {o.seller_data_complete === false && (
          <div className="mx-6 mb-3 rounded-md bg-status-amberBg border border-status-amber/30 text-charcoal-800 text-[13px] px-3 py-2">
            <span className="font-semibold text-charcoal-900">
              Seller-side data incomplete.
            </span>{" "}
            Fit claims below are assumptions.{" "}
            <Link
              href="/settings/company-profile"
              className="text-steel-700 underline hover:text-charcoal-900"
            >
              Complete the Company Profile
            </Link>{" "}
            and regenerate for a grounded win/deliver verdict.
          </div>
        )}

        <BriefingSection eyebrow="Verdict" title="Can we credibly win and deliver?">
          <div className="flex items-start gap-3">
            <div className="flex-1">
              <p className="text-[15px] leading-relaxed whitespace-pre-line">
                {o.win_assessment || "—"}
              </p>
              <p className="mt-3 text-[14px] text-charcoal-700 leading-relaxed">
                {o.executive_summary || "—"}
              </p>
            </div>
            <StatusPill tone={fitTone(o.fit_score)}>
              Fit: {o.fit_score ?? "—"}
            </StatusPill>
          </div>
        </BriefingSection>

        <BriefingSection eyebrow="Fit" title="Where we are strong and weak">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <div className="miq-eyebrow mb-2">Strong fit areas</div>
              <div className="flex flex-col gap-2">
                {(o.strong_fit_areas ?? []).map((f, i) => (
                  <FitCard key={i} fit={f} tone="green" />
                ))}
                {(o.strong_fit_areas?.length ?? 0) === 0 && (
                  <p className="text-[13px] text-charcoal-500">None identified.</p>
                )}
              </div>
            </div>
            <div>
              <div className="miq-eyebrow mb-2">Weak fit areas</div>
              <div className="flex flex-col gap-2">
                {(o.weak_fit_areas ?? []).map((f, i) => (
                  <FitCard key={i} fit={f} tone="red" />
                ))}
                {(o.weak_fit_areas?.length ?? 0) === 0 && (
                  <p className="text-[13px] text-charcoal-500">None identified.</p>
                )}
              </div>
            </div>
          </div>
        </BriefingSection>

        <BriefingSection eyebrow="Gaps" title="What is missing & what we must prove">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Column label="Missing capabilities" items={o.missing_capabilities} />
            <Column label="Required proof points" items={o.required_proof_points} />
          </div>
        </BriefingSection>

        {(o.recommended_teaming_partners?.length ?? 0) > 0 && (
          <BriefingSection eyebrow="Teaming" title="Recommended teaming partners">
            <div className="flex flex-col gap-2">
              {(o.recommended_teaming_partners ?? []).map(
                (t: TeamingRecommendation, i) => (
                  <div
                    key={i}
                    className="rounded-md border border-charcoal-200 px-3 py-2.5"
                  >
                    <div className="font-semibold text-[14px] text-charcoal-900">
                      {t.partner_profile}
                    </div>
                    <div className="text-[12px] text-steel-700 mt-0.5">
                      Fills gap: {t.fills_gap}
                    </div>
                    <p className="mt-1 text-[13px] text-charcoal-700">
                      {t.rationale}
                    </p>
                  </div>
                ),
              )}
            </div>
          </BriefingSection>
        )}

        <BriefingSection eyebrow="Positioning" title="Discriminators & win themes">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Column
              label="Suggested discriminators"
              items={o.suggested_discriminators}
            />
            <Column label="Reusable win themes" items={o.reusable_win_themes} />
          </div>
        </BriefingSection>

        {(o.capture_questions?.length ?? 0) > 0 && (
          <BriefingSection
            eyebrow="Intel gaps"
            title="Capture questions to close before bid decision"
          >
            <BulletList items={o.capture_questions ?? []} />
          </BriefingSection>
        )}

        {(o.proposal_risks?.length ?? 0) > 0 && (
          <BriefingSection
            eyebrow="Risk"
            title="Proposal risks tied to company gaps"
          >
            <div className="flex flex-col gap-2">
              {(o.proposal_risks ?? []).map((r: CompanyGapRisk, i) => (
                <div
                  key={i}
                  className="rounded-md border border-charcoal-200 px-3 py-2.5"
                >
                  <div className="flex items-center justify-between gap-2">
                    <div className="font-semibold text-[14px] text-charcoal-900">
                      {r.title}
                    </div>
                    <StatusPill tone={severityTone(r.severity)}>
                      {r.severity ?? "—"}
                    </StatusPill>
                  </div>
                  <p className="mt-1 text-[13px] text-charcoal-700">
                    {r.description}
                  </p>
                  <p className="mt-1 text-[13px] text-charcoal-700">
                    <span className="font-medium">Mitigation:</span>{" "}
                    {r.mitigation}
                  </p>
                </div>
              ))}
            </div>
          </BriefingSection>
        )}

        {(o.recommended_actions?.length ?? 0) > 0 && (
          <BriefingSection eyebrow="Next moves" title="Recommended actions">
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

export default function CapabilityMatchPage({
  params,
}: {
  params: Promise<{ opportunityId: string }>;
}) {
  const { opportunityId } = use(params);
  return (
    <div>
      <PageHeader
        eyebrow="Capture Intelligence · Fit assessment"
        title="Capability Match"
        subtitle={
          "A senior-capture-lead assessment of whether you can credibly win " +
          "and deliver. MissionIQ compares Customer DNA, opportunity " +
          "requirements, evaluation criteria, market intelligence, and your " +
          "Company Profile to surface strong/weak fit, gaps, proof points, " +
          "teaming, discriminators, win themes, and company-gap risks."
        }
      />
      <ModuleWorkbench
        opportunityId={opportunityId}
        moduleId="capture.capability_match"
        moduleLabel="Capability Match"
        description={
          "Run the fit assessment. Requires a Customer DNA Profile and reads " +
          "your Company Profile (generate Company DNA first for the sharpest " +
          "result). Without a Company Profile it still runs, but seller-side " +
          "claims are clearly labeled as assumptions."
        }
        outputRenderer={renderMatch}
      />
    </div>
  );
}
