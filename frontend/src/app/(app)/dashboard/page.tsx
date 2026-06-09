"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { apiRequest } from "@/lib/api";
import type { Opportunity } from "@/lib/types";
import { PageHeader } from "@/components/PageHeader";
import { KpiCard } from "@/components/ds/KpiCard";
import { Card, CardBody, CardHeader } from "@/components/ds/Card";
import { DataTable } from "@/components/ds/DataTable";
import { StatusPill } from "@/components/ds/StatusPill";
import { Button } from "@/components/ds/Button";
import { Skeleton } from "@/components/ds/Skeleton";
import { Target } from "lucide-react";
import { captureStageLabel, daysUntil, formatCurrencyCents, formatDate } from "@/lib/format";

export default function DashboardPage() {
  const { currentWorkspaceId, memberships } = useAuth();
  const [opps, setOpps] = useState<Opportunity[] | null>(null);

  useEffect(() => {
    if (!currentWorkspaceId) return;
    apiRequest<Opportunity[]>(`/workspaces/${currentWorkspaceId}/opportunities?limit=10`)
      .then(setOpps)
      .catch(() => setOpps([]));
  }, [currentWorkspaceId]);

  const current = memberships.find((m) => m.workspace_id === currentWorkspaceId);

  const total = opps?.length ?? 0;
  const dueSoon = opps?.filter((o) => {
    const d = daysUntil(o.due_date);
    return d != null && d >= 0 && d <= 30;
  }).length ?? 0;
  const inCapture = opps?.filter((o) =>
    ["capture", "proposal"].includes(o.capture_stage),
  ).length ?? 0;
  const pipelineValue = opps?.reduce(
    (acc, o) => acc + (o.estimated_value_cents ?? 0),
    0,
  ) ?? 0;

  return (
    <div>
      <PageHeader
        eyebrow="MissionIQ · Executive Dashboard"
        title={current?.workspace_name ?? "Workspace"}
        subtitle="A briefing-level view of your operational intelligence."
        actions={
          <Link href="/capture/opportunities/new">
            <Button>New opportunity</Button>
          </Link>
        }
      />

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <KpiCard label="Opportunities Tracked" value={total} helper="In this workspace" />
        <KpiCard
          label="Due Within 30 Days"
          value={dueSoon}
          tone={dueSoon > 0 ? "amber" : undefined}
          helper="Action required"
        />
        <KpiCard label="In Capture / Proposal" value={inCapture} />
        <KpiCard
          label="Estimated Pipeline"
          value={formatCurrencyCents(pipelineValue)}
          helper="Sum of estimated values"
        />
      </div>

      <Card>
        <CardHeader
          eyebrow="Capture Intelligence"
          title="Recent opportunities"
          actions={
            <Link href="/capture/opportunities">
              <Button variant="secondary" size="sm">View all</Button>
            </Link>
          }
        />
        <CardBody className="!p-0">
          {opps === null ? (
            <div className="p-6 flex flex-col gap-2">
              {[0, 1, 2].map((i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          ) : (
            <DataTable
              columns={[
                {
                  key: "name",
                  header: "Opportunity",
                  render: (o) => (
                    <Link
                      href={`/capture/opportunities/${o.id}`}
                      className="font-medium text-charcoal-900 hover:underline"
                    >
                      {o.name}
                    </Link>
                  ),
                },
                { key: "agency", header: "Agency", render: (o) => o.agency || "—" },
                {
                  key: "stage",
                  header: "Stage",
                  render: (o) => (
                    <StatusPill
                      tone={
                        o.capture_stage === "capture" || o.capture_stage === "proposal"
                          ? "info"
                          : o.capture_stage === "no-bid" || o.capture_stage === "lost"
                            ? "red"
                            : "neutral"
                      }
                    >
                      {captureStageLabel(o.capture_stage)}
                    </StatusPill>
                  ),
                },
                {
                  key: "due",
                  header: "Due",
                  render: (o) => formatDate(o.due_date),
                },
                {
                  key: "value",
                  header: "Est. Value",
                  align: "right",
                  render: (o) => (
                    <span className="miq-numeric">
                      {formatCurrencyCents(o.estimated_value_cents)}
                    </span>
                  ),
                },
              ]}
              rows={opps}
              emptyState={
                <div className="p-6">
                  <div className="text-h3 text-charcoal-900">
                    No opportunities yet.
                  </div>
                  <p className="text-charcoal-500 mt-1 text-[14px]">
                    Create your first opportunity to begin building capture intelligence.
                  </p>
                  <Link href="/capture/opportunities/new" className="inline-block mt-4">
                    <Button>
                      <Target className="h-4 w-4" />
                      New opportunity
                    </Button>
                  </Link>
                </div>
              }
            />
          )}
        </CardBody>
      </Card>
    </div>
  );
}
