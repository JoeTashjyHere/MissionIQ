"use client";

import { use } from "react";
import clsx from "clsx";
import { PageHeader } from "@/components/PageHeader";
import { ModuleWorkbench } from "@/components/intelligence/ModuleWorkbench";
import { BriefingSection, BulletList } from "@/components/ds/BriefingSection";
import { StatusPill } from "@/components/ds/StatusPill";
import type { AIOutput, ComplianceMatrixOutput, ComplianceRow } from "@/lib/types";

const PRIORITY_TONE: Record<
  ComplianceRow["customer_priority"],
  "red" | "amber" | "neutral" | "green"
> = {
  critical: "red",
  high: "red",
  medium: "amber",
  low: "neutral",
};

function priorityRank(p: ComplianceRow["customer_priority"]): number {
  return { critical: 0, high: 1, medium: 2, low: 3 }[p];
}

function renderCompliance(output: AIOutput) {
  const o = output.output_json as unknown as ComplianceMatrixOutput;
  const rows = [...(o.rows ?? [])].sort(
    (a, b) => priorityRank(a.customer_priority) - priorityRank(b.customer_priority),
  );

  return (
    <div className="-mx-6">
      <BriefingSection eyebrow="Executive summary" title="What this matrix tells the capture team">
        <p>{o.executive_summary || "—"}</p>
      </BriefingSection>

      {(o.key_findings?.length ?? 0) > 0 && (
        <BriefingSection eyebrow="Key findings" title="Patterns across requirements">
          <BulletList items={o.key_findings ?? []} />
        </BriefingSection>
      )}

      <BriefingSection
        eyebrow="Requirements"
        title={`Compliance rows (${rows.length})`}
      >
        {rows.length === 0 ? (
          <p className="text-charcoal-500 italic text-[13px]">
            No requirements extracted yet.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-[1200px] text-[12.5px] border-collapse">
              <thead>
                <tr className="text-charcoal-500 border-b border-charcoal-200">
                  <Th>ID</Th>
                  <Th>Requirement</Th>
                  <Th>Source</Th>
                  <Th>Category</Th>
                  <Th>Why it exists</Th>
                  <Th>Mission alignment</Th>
                  <Th>Customer priority</Th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r, i) => (
                  <tr
                    key={i}
                    className="border-b border-charcoal-100 align-top"
                  >
                    <Td className="font-mono text-[12px] whitespace-nowrap">
                      {r.requirement_id}
                    </Td>
                    <Td className="max-w-[320px]">
                      <div className="text-charcoal-900">
                        {r.requirement_text}
                      </div>
                      {r.notes && (
                        <div className="mt-1 text-charcoal-500 text-[11.5px]">
                          {r.notes}
                        </div>
                      )}
                    </Td>
                    <Td className="text-charcoal-700 text-[11.5px] whitespace-nowrap">
                      {r.source_document && (
                        <div>
                          {r.source_document}
                          {r.source_page ? ` · p.${r.source_page}` : ""}
                        </div>
                      )}
                      {r.source_section && (
                        <div className="text-charcoal-500">
                          {r.source_section}
                        </div>
                      )}
                    </Td>
                    <Td className="text-charcoal-700 whitespace-nowrap">
                      {r.category ?? "—"}
                    </Td>
                    <Td className="max-w-[260px] text-charcoal-700">
                      {r.why_requirement_exists}
                    </Td>
                    <Td className="max-w-[260px] text-charcoal-700">
                      {r.mission_alignment}
                    </Td>
                    <Td className="whitespace-nowrap">
                      <StatusPill tone={PRIORITY_TONE[r.customer_priority]}>
                        {r.customer_priority}
                      </StatusPill>
                    </Td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </BriefingSection>

      {(o.coverage_gaps?.length ?? 0) > 0 && (
        <BriefingSection
          eyebrow="Coverage gaps"
          title="Requirements we suspect exist but aren't in the evidence"
        >
          <BulletList items={o.coverage_gaps ?? []} />
        </BriefingSection>
      )}

      {(o.recommended_actions?.length ?? 0) > 0 && (
        <BriefingSection
          eyebrow="Next moves"
          title="Where to invest writing time and SMEs"
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

function Th({ children }: { children: React.ReactNode }) {
  return (
    <th className="text-left font-medium pb-2 pr-4 uppercase tracking-wide text-[11px]">
      {children}
    </th>
  );
}

function Td({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return <td className={clsx("py-2 pr-4", className)}>{children}</td>;
}

export default function CompliancePage({
  params,
}: {
  params: Promise<{ opportunityId: string }>;
}) {
  const { opportunityId } = use(params);
  return (
    <div>
      <PageHeader
        eyebrow="Capture Intelligence"
        title="Compliance Matrix"
        subtitle={
          "Consultant-grade compliance analysis. Every row carries why the " +
          "requirement exists, how it ladders into the customer's mission, " +
          "and the customer's relative priority — informed by the Customer " +
          "DNA Profile. Generate the DNA Profile first."
        }
      />
      <ModuleWorkbench
        opportunityId={opportunityId}
        moduleId="capture.compliance_matrix"
        moduleLabel="Compliance Matrix"
        description={
          "Decompose the RFP into a prioritized matrix shaped by the Customer " +
          "DNA Profile, with mission alignment and customer-priority columns."
        }
        outputRenderer={renderCompliance}
      />
    </div>
  );
}
