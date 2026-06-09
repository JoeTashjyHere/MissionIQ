"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { apiRequest } from "@/lib/api";
import type { Opportunity } from "@/lib/types";
import { PageHeader } from "@/components/PageHeader";
import { Card, CardBody, CardHeader } from "@/components/ds/Card";
import { DataTable } from "@/components/ds/DataTable";
import { StatusPill } from "@/components/ds/StatusPill";
import { Button } from "@/components/ds/Button";
import { Skeleton } from "@/components/ds/Skeleton";
import { captureStageLabel, formatCurrencyCents, formatDate } from "@/lib/format";

export default function OpportunitiesPage() {
  const { currentWorkspaceId } = useAuth();
  const [items, setItems] = useState<Opportunity[] | null>(null);

  useEffect(() => {
    if (!currentWorkspaceId) return;
    apiRequest<Opportunity[]>(`/workspaces/${currentWorkspaceId}/opportunities`)
      .then(setItems)
      .catch(() => setItems([]));
  }, [currentWorkspaceId]);

  return (
    <div>
      <PageHeader
        eyebrow="Capture Intelligence"
        title="Opportunities"
        subtitle="All opportunities in this workspace."
        actions={
          <Link href="/capture/opportunities/new">
            <Button>New opportunity</Button>
          </Link>
        }
      />

      <Card>
        <CardHeader title="Pipeline" subtitle="Filterable list of all opportunities." />
        <CardBody className="!p-0">
          {items === null ? (
            <div className="p-6 flex flex-col gap-2">
              {[0, 1, 2, 3].map((i) => (
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
                { key: "solicitation", header: "Solicitation", render: (o) => o.solicitation_number || "—" },
                { key: "agency", header: "Agency", render: (o) => o.agency || "—" },
                {
                  key: "stage",
                  header: "Stage",
                  render: (o) => (
                    <StatusPill
                      tone={
                        o.capture_stage === "awarded"
                          ? "green"
                          : o.capture_stage === "lost" || o.capture_stage === "no-bid"
                            ? "red"
                            : "info"
                      }
                    >
                      {captureStageLabel(o.capture_stage)}
                    </StatusPill>
                  ),
                },
                { key: "due", header: "Due", render: (o) => formatDate(o.due_date) },
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
              rows={items}
              emptyState={
                <div className="p-10 text-center">
                  <div className="text-h3">No opportunities yet</div>
                  <p className="text-charcoal-500 text-[14px] mt-1">
                    Create your first opportunity to start building capture intelligence.
                  </p>
                  <Link href="/capture/opportunities/new" className="inline-block mt-4">
                    <Button>New opportunity</Button>
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
