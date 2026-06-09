"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { apiRequest } from "@/lib/api";
import type { OpportunityOverview } from "@/lib/types";
import { PageHeader } from "@/components/PageHeader";
import { KpiCard } from "@/components/ds/KpiCard";
import { Card, CardBody, CardHeader } from "@/components/ds/Card";
import { StatusPill } from "@/components/ds/StatusPill";
import { Button } from "@/components/ds/Button";
import { Skeleton } from "@/components/ds/Skeleton";
import {
  captureStageLabel,
  daysUntil,
  formatCurrencyCents,
  formatDate,
  formatDateTime,
} from "@/lib/format";

export default function OpportunityBriefingPage({
  params,
}: {
  params: Promise<{ opportunityId: string }>;
}) {
  const { opportunityId } = use(params);
  const [overview, setOverview] = useState<OpportunityOverview | null>(null);

  useEffect(() => {
    apiRequest<OpportunityOverview>(`/opportunities/${opportunityId}/overview`)
      .then(setOverview)
      .catch(() => setOverview(null));
  }, [opportunityId]);

  if (!overview) {
    return (
      <div className="flex flex-col gap-4">
        <Skeleton className="h-10 w-1/2" />
        <Skeleton className="h-24" />
        <Skeleton className="h-64" />
      </div>
    );
  }
  const opp = overview.opportunity;
  const due = daysUntil(opp.due_date);
  const dueTone: "amber" | "red" | undefined =
    due == null ? undefined : due < 0 ? "red" : due <= 14 ? "amber" : undefined;

  return (
    <div>
      <PageHeader
        eyebrow={`Capture Intelligence · ${captureStageLabel(opp.capture_stage)}`}
        title={opp.name}
        subtitle={
          <div className="flex flex-wrap gap-x-4 gap-y-1 text-[13px] text-charcoal-500">
            {opp.agency && <span>{opp.agency}</span>}
            {opp.solicitation_number && (
              <span className="font-mono">{opp.solicitation_number}</span>
            )}
            {opp.due_date && <span>Due {formatDate(opp.due_date)}</span>}
            {opp.estimated_value_cents != null && (
              <span>{formatCurrencyCents(opp.estimated_value_cents)}</span>
            )}
          </div>
        }
        actions={
          <Link href={`/capture/opportunities/${opp.id}/summary`}>
            <Button>Open Summary</Button>
          </Link>
        }
      />

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <KpiCard
          label="Documents Ready"
          value={`${overview.ready_document_count} / ${overview.document_count}`}
          helper="Ingested and indexed"
        />
        <KpiCard
          label="AI Generations"
          value={overview.ai_output_count}
          helper={overview.last_ai_generation_at ? `Last: ${formatDateTime(overview.last_ai_generation_at)}` : "None yet"}
        />
        <KpiCard
          label="Compliance Items"
          value={`${overview.compliance_complete} / ${overview.compliance_total}`}
          helper="Complete / total"
        />
        <KpiCard
          label="Risks Open"
          value={overview.open_risk_count}
          tone={overview.open_risk_count > 0 ? "amber" : "green"}
          helper={`${overview.risk_count} total`}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-2">
          <CardHeader eyebrow="Opportunity Briefing" title="At a glance" />
          <CardBody>
            <dl className="grid grid-cols-2 gap-x-6 gap-y-4 text-[14px]">
              <Field label="Agency" value={opp.agency || "—"} />
              <Field label="Sub-agency" value={opp.sub_agency || "—"} />
              <Field label="Solicitation #" value={opp.solicitation_number || "—"} mono />
              <Field label="Contract vehicle" value={opp.contract_vehicle || "—"} />
              <Field label="NAICS" value={opp.naics_code || "—"} mono />
              <Field label="PSC" value={opp.psc_code || "—"} mono />
              <Field label="Set-aside" value={opp.set_aside || "—"} />
              <Field label="Incumbent" value={opp.incumbent || "—"} />
              <Field label="Posted" value={formatDate(opp.posted_date)} />
              <Field label="Due" value={formatDate(opp.due_date)} />
              <Field
                label="Est. value"
                value={formatCurrencyCents(opp.estimated_value_cents)}
              />
              <Field
                label="Stage"
                value={
                  <StatusPill tone="info">
                    {captureStageLabel(opp.capture_stage)}
                  </StatusPill>
                }
              />
            </dl>
            {opp.notes && (
              <div className="mt-6 border-t border-charcoal-100 pt-4">
                <div className="miq-eyebrow mb-1">Notes</div>
                <p className="text-[14px] text-charcoal-900 whitespace-pre-wrap">
                  {opp.notes}
                </p>
              </div>
            )}
          </CardBody>
        </Card>

        <Card>
          <CardHeader title="Time to response" />
          <CardBody>
            {due == null ? (
              <p className="text-charcoal-500 text-[14px]">No due date set.</p>
            ) : due < 0 ? (
              <div>
                <StatusPill tone="red">Past due</StatusPill>
                <p className="text-charcoal-500 text-[13px] mt-2">
                  Due date was {formatDate(opp.due_date)}.
                </p>
              </div>
            ) : (
              <div>
                <div className="miq-numeric text-[40px] font-semibold leading-none">
                  {due}
                </div>
                <div className="text-charcoal-500 text-[13px] mt-1">
                  days until {formatDate(opp.due_date)}
                </div>
                {dueTone && (
                  <div className="mt-3">
                    <StatusPill tone={dueTone}>
                      {due <= 14 ? "Window closing" : "On the radar"}
                    </StatusPill>
                  </div>
                )}
              </div>
            )}
          </CardBody>
        </Card>
      </div>
    </div>
  );
}

function Field({
  label,
  value,
  mono,
}: {
  label: string;
  value: React.ReactNode;
  mono?: boolean;
}) {
  return (
    <div>
      <dt className="miq-eyebrow text-[11px]">{label}</dt>
      <dd
        className={`mt-0.5 text-charcoal-900 ${mono ? "font-mono text-[13px]" : ""}`}
      >
        {value}
      </dd>
    </div>
  );
}
