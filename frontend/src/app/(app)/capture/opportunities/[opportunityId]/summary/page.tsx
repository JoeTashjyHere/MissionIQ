"use client";

import { use } from "react";
import { PageHeader } from "@/components/PageHeader";
import { ModuleWorkbench } from "@/components/intelligence/ModuleWorkbench";
import { BriefingSection, BulletList } from "@/components/ds/BriefingSection";
import type { AIOutput, Citation } from "@/lib/types";

interface SupportingEvidenceItem {
  evidence_ref: string;
  finding: string;
}

interface SummaryOutput {
  executive_summary?: string;
  key_findings?: string[];
  supporting_evidence?: SupportingEvidenceItem[];
  recommended_actions?: string[];

  mission_need?: string | null;
  scope_summary?: string | null;
  key_services?: string[];
  deliverables?: string[];
  timeline?: string | null;
  risks?: string[];
  pursue_indicators?: string[];
  no_pursue_indicators?: string[];

  _notice?: string;
}

function evidenceToCitation(
  ref: string,
  citations: Citation[],
): Citation | null {
  // E1/M1 → index 0 in the corresponding sub-list (document chunks vs market intel).
  const m = ref.trim().toUpperCase().match(/^([EM])(\d+)$/);
  if (!m) return null;
  const idx = parseInt(m[2], 10) - 1;
  if (Number.isNaN(idx) || idx < 0) return null;
  const subset =
    m[1] === "E"
      ? citations.filter((c) => c.type === "document_chunk")
      : citations.filter((c) => c.type === "market_intel_record");
  return subset[idx] ?? null;
}

function renderSummary(output: AIOutput) {
  const o = output.output_json as SummaryOutput;
  const supporting = o.supporting_evidence ?? [];

  return (
    <div className="-mx-6">
      {o._notice && (
        <div className="mx-6 mb-3 rounded-md bg-steel-700/10 text-steel-700 text-[12px] px-3 py-2">
          {o._notice}
        </div>
      )}

      <BriefingSection eyebrow="Section 1 · Executive Summary" title="Bottom line">
        <p className="text-[15px] leading-relaxed">{o.executive_summary || "—"}</p>
      </BriefingSection>

      <BriefingSection eyebrow="Section 2 · Key Findings" title="What the analysis surfaced">
        <BulletList items={o.key_findings ?? []} />
      </BriefingSection>

      <BriefingSection
        eyebrow="Section 3 · Supporting Evidence"
        title="How each finding is sourced"
      >
        {supporting.length === 0 ? (
          <p className="text-charcoal-500 italic text-[13px]">
            No supporting evidence references were emitted. Findings should be
            treated as unverified.
          </p>
        ) : (
          <ul className="space-y-2">
            {supporting.map((s, i) => {
              const cit = evidenceToCitation(s.evidence_ref, output.citations);
              const label =
                cit?.type === "document_chunk"
                  ? `${cit.document_name} · p.${cit.page_start ?? "?"}`
                  : cit?.type === "market_intel_record"
                    ? `${cit.source_id.toUpperCase()} · ${cit.title}`
                    : s.evidence_ref;
              return (
                <li
                  key={i}
                  className="rounded-md border border-charcoal-100 px-3 py-2 bg-white"
                >
                  <div className="flex items-center gap-2 text-[12px] text-charcoal-500">
                    <span className="font-mono text-steel-700">[{s.evidence_ref}]</span>
                    <span>{label}</span>
                  </div>
                  <div className="mt-1 text-[14px] text-charcoal-900">{s.finding}</div>
                </li>
              );
            })}
          </ul>
        )}
      </BriefingSection>

      <BriefingSection
        eyebrow="Section 4 · Recommended Actions"
        title="What the capture team should do next"
      >
        {(o.recommended_actions ?? []).length === 0 ? (
          <p className="text-charcoal-500 italic text-[13px]">No actions recommended.</p>
        ) : (
          <ol className="list-decimal pl-5 space-y-1.5 text-[14px]">
            {(o.recommended_actions ?? []).map((a, i) => (
              <li key={i}>{a}</li>
            ))}
          </ol>
        )}
      </BriefingSection>

      <BriefingSection eyebrow="Detail · Mission & scope" title="Structured detail">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Block label="Mission need" body={o.mission_need ?? undefined} />
          <Block label="Scope summary" body={o.scope_summary ?? undefined} />
        </div>
        <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <div className="miq-eyebrow mb-1">Key services</div>
            <BulletList items={o.key_services ?? []} />
          </div>
          <div>
            <div className="miq-eyebrow mb-1">Deliverables</div>
            <BulletList items={o.deliverables ?? []} />
          </div>
        </div>
        <div className="mt-4">
          <div className="miq-eyebrow mb-1">Timeline</div>
          <p className="whitespace-pre-line text-[14px]">{o.timeline || "—"}</p>
        </div>
      </BriefingSection>

      <BriefingSection eyebrow="Detail · Risks" title="Surfaced risks">
        <BulletList items={o.risks ?? []} />
      </BriefingSection>

      <BriefingSection eyebrow="Detail · Decision" title="Pursue / No-pursue indicators">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <div className="miq-eyebrow text-status-green mb-1">Pursue indicators</div>
            <BulletList items={o.pursue_indicators ?? []} />
          </div>
          <div>
            <div className="miq-eyebrow text-status-red mb-1">No-pursue indicators</div>
            <BulletList items={o.no_pursue_indicators ?? []} />
          </div>
        </div>
      </BriefingSection>
    </div>
  );
}

function Block({ label, body }: { label: string; body?: string }) {
  return (
    <div>
      <div className="miq-eyebrow mb-1">{label}</div>
      <p className="text-[14px] text-charcoal-900 whitespace-pre-wrap">{body || "—"}</p>
    </div>
  );
}

export default function SummaryPage({
  params,
}: {
  params: Promise<{ opportunityId: string }>;
}) {
  const { opportunityId } = use(params);
  return (
    <div>
      <PageHeader
        eyebrow="Capture Intelligence"
        title="Opportunity Summary"
        subtitle="Executive briefing derived from uploaded documents. Every finding is traceable to its source."
      />
      <ModuleWorkbench
        opportunityId={opportunityId}
        moduleId="capture.opportunity_summary"
        moduleLabel="Opportunity Summary"
        description="Generate a four-section executive briefing — Executive Summary, Key Findings, Supporting Evidence, Recommended Actions — grounded in the documents you've uploaded for this opportunity."
        outputRenderer={renderSummary}
      />
    </div>
  );
}
