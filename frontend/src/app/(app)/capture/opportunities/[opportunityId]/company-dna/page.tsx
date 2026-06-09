"use client";

import { use } from "react";
import Link from "next/link";
import { PageHeader } from "@/components/PageHeader";
import { ModuleWorkbench } from "@/components/intelligence/ModuleWorkbench";
import { BriefingSection, BulletList } from "@/components/ds/BriefingSection";
import { StatusPill } from "@/components/ds/StatusPill";
import type { AIOutput, CompanyDnaProfile } from "@/lib/types";

function confidenceTone(c?: string): "green" | "amber" | "red" | "neutral" {
  if (c === "high") return "green";
  if (c === "medium") return "amber";
  if (c === "low" || c === "insufficient") return "red";
  return "neutral";
}

function renderDna(output: AIOutput) {
  const o = output.output_json as unknown as CompanyDnaProfile;

  if (o.profile_completeness === "empty") {
    return (
      <div className="rounded-md bg-status-amberBg border border-status-amber/30 text-charcoal-800 text-[13px] px-4 py-3">
        <div className="font-semibold text-charcoal-900">
          Company Profile is empty
        </div>
        <p className="mt-1">
          MissionIQ cannot assess whether you can credibly win and deliver
          without seller-side data.{" "}
          <Link
            href="/settings/company-profile"
            className="text-steel-700 underline hover:text-charcoal-900"
          >
            Complete the Company Profile
          </Link>{" "}
          (capabilities, past performance, certifications, differentiators,
          delivery model), then regenerate.
        </p>
        {(o.recommended_actions?.length ?? 0) > 0 && (
          <ol className="mt-3 list-decimal pl-5 space-y-1">
            {(o.recommended_actions ?? []).map((a, i) => (
              <li key={i}>{a}</li>
            ))}
          </ol>
        )}
      </div>
    );
  }

  return (
    <div className="-mx-6">
      <BriefingSection eyebrow="Identity" title="Who we are">
        <div className="flex items-start gap-3">
          <div className="flex-1">
            <p className="text-[15px] leading-relaxed whitespace-pre-line">
              {o.company_summary || "—"}
            </p>
            <p className="mt-3 text-[14px] text-charcoal-700 leading-relaxed">
              {o.executive_summary || "—"}
            </p>
          </div>
          <div className="flex flex-col items-end gap-1.5">
            <StatusPill tone={confidenceTone(o.confidence)}>
              {o.confidence ? `Confidence: ${o.confidence}` : "Confidence: —"}
            </StatusPill>
            {o.profile_completeness && (
              <StatusPill
                tone={
                  o.profile_completeness === "complete" ? "green" : "amber"
                }
              >
                Profile: {o.profile_completeness}
              </StatusPill>
            )}
          </div>
        </div>
      </BriefingSection>

      <BriefingSection eyebrow="What we bring" title="Capabilities & differentiators">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Column label="Core capabilities" items={o.core_capabilities} />
          <Column label="Differentiators" items={o.differentiators} />
        </div>
      </BriefingSection>

      <BriefingSection eyebrow="Proof" title="Past performance & case studies">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Column label="Past performance" items={o.past_performance} />
          <Column label="Case studies" items={o.case_studies} />
        </div>
      </BriefingSection>

      <BriefingSection eyebrow="Access" title="Vehicles, certifications & partners">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Column label="Contract vehicles" items={o.contract_vehicles} />
          <Column label="Certifications" items={o.certifications} />
          <Column label="Technology partners" items={o.technology_partners} />
        </div>
      </BriefingSection>

      <BriefingSection eyebrow="Delivery" title="How we deliver">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Field label="Delivery model" value={o.delivery_model} />
          <Field label="Security posture" value={o.security_posture} />
          <Field label="Geographic footprint" value={o.geographic_footprint} />
          <Field label="Pricing posture" value={o.pricing_posture} />
        </div>
        {(o.key_personnel?.length ?? 0) > 0 && (
          <div className="mt-6">
            <Column label="Key personnel / SMEs" items={o.key_personnel} />
          </div>
        )}
      </BriefingSection>

      {(o.key_findings?.length ?? 0) > 0 && (
        <BriefingSection eyebrow="Findings" title="Key analyst findings">
          <BulletList items={o.key_findings ?? []} />
        </BriefingSection>
      )}

      {(o.recommended_actions?.length ?? 0) > 0 && (
        <BriefingSection
          eyebrow="Next moves"
          title="Strengthen the Company Profile"
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

function Field({ label, value }: { label: string; value?: string | null }) {
  return (
    <div>
      <div className="miq-eyebrow mb-1">{label}</div>
      <p className="text-[14px] text-charcoal-700 leading-relaxed">
        {value || "—"}
      </p>
    </div>
  );
}

export default function CompanyDnaPage({
  params,
}: {
  params: Promise<{ opportunityId: string }>;
}) {
  const { opportunityId } = use(params);
  return (
    <div>
      <PageHeader
        eyebrow="Capture Intelligence · Seller-side synthesis"
        title="Company DNA Profile"
        subtitle={
          "The seller-side mirror of Customer DNA. MissionIQ synthesizes the " +
          "company pursuing this work — core capabilities, past performance, " +
          "vehicles, certifications, partners, differentiators, delivery model, " +
          "and security posture — from your Company Profile. Capability Match " +
          "reads this to judge whether you can credibly win and deliver."
        }
      />
      <ModuleWorkbench
        opportunityId={opportunityId}
        moduleId="capture.company_dna"
        moduleLabel="Company DNA Profile"
        description={
          "Synthesize a Company DNA Profile from your workspace Company " +
          "Profile and capability catalog. This is the seller-side input to " +
          "Capability Match. Keep your Company Profile current for a sharper " +
          "fit assessment."
        }
        requiresDocuments={false}
        outputRenderer={renderDna}
      />
    </div>
  );
}
