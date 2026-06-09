"use client";

import { useEffect, useMemo, useState } from "react";
import { History } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { apiRequest } from "@/lib/api";
import type { Connector, SyncJob } from "@/lib/types";
import {
  SYNC_IN_FLIGHT,
  SYNC_STATUS_LABEL,
  syncProgressTone,
  syncStatsSummary,
  syncStatusTone,
} from "@/lib/integrations";
import { formatDateTime } from "@/lib/format";
import { PageHeader } from "@/components/PageHeader";
import { Badge } from "@/components/ds/Badge";
import { Card, CardBody, CardHeader } from "@/components/ds/Card";
import { DataTable } from "@/components/ds/DataTable";
import { EmptyState } from "@/components/ds/EmptyState";
import { ProgressBar } from "@/components/ds/ProgressBar";
import { Select } from "@/components/ds/Select";
import { StatusPill } from "@/components/ds/StatusPill";

function duration(job: SyncJob): string {
  if (!job.started_at || !job.finished_at) return "—";
  const ms = new Date(job.finished_at).getTime() - new Date(job.started_at).getTime();
  if (ms < 1000) return "<1s";
  return `${Math.round(ms / 1000)}s`;
}

export default function SyncHistoryPage() {
  const { currentWorkspaceId } = useAuth();
  const [jobs, setJobs] = useState<SyncJob[] | null>(null);
  const [connectors, setConnectors] = useState<Connector[]>([]);
  const [connectorFilter, setConnectorFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  useEffect(() => {
    if (!currentWorkspaceId) return;
    const refresh = () =>
      apiRequest<SyncJob[]>(`/workspaces/${currentWorkspaceId}/sync-jobs?limit=100`)
        .then(setJobs)
        .catch(() => setJobs((prev) => prev ?? []));
    refresh();
    apiRequest<Connector[]>(`/workspaces/${currentWorkspaceId}/connectors`)
      .then(setConnectors)
      .catch(() => setConnectors([]));
    const t = setInterval(refresh, 2500);
    return () => clearInterval(t);
  }, [currentWorkspaceId]);

  const filtered = useMemo(
    () =>
      (jobs ?? []).filter(
        (j) =>
          (!connectorFilter || j.connector_id === connectorFilter) &&
          (!statusFilter || j.status === statusFilter),
      ),
    [jobs, connectorFilter, statusFilter],
  );

  const inFlight = (jobs ?? []).filter((j) =>
    SYNC_IN_FLIGHT.includes(j.status),
  ).length;

  return (
    <div>
      <PageHeader
        eyebrow="MissionIQ · Integrations"
        title="Sync History"
        subtitle="Every connector sync job, its outcome, and what it ingested."
      />

      <Card>
        <CardHeader
          title="Sync jobs"
          eyebrow="Most recent first"
          subtitle={
            inFlight > 0 ? `${inFlight} job(s) in progress — updating live.` : undefined
          }
          actions={
            <div className="flex items-center gap-2">
              <Select
                value={connectorFilter}
                onChange={(e) => setConnectorFilter(e.target.value)}
                aria-label="Filter by connector"
              >
                <option value="">All connectors</option>
                {connectors.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </Select>
              <Select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                aria-label="Filter by status"
              >
                <option value="">All statuses</option>
                {Object.entries(SYNC_STATUS_LABEL).map(([k, v]) => (
                  <option key={k} value={k}>
                    {v}
                  </option>
                ))}
              </Select>
            </div>
          }
        />
        <CardBody className="!p-0">
          {jobs !== null && jobs.length === 0 ? (
            <div className="p-6">
              <EmptyState
                icon={<History />}
                title="No sync jobs yet"
                description="Trigger a sync from the Connectors page to see job history here."
              />
            </div>
          ) : (
            <DataTable
              columns={[
                {
                  key: "connector",
                  header: "Connector",
                  render: (j: SyncJob) => (
                    <div>
                      <div className="font-medium">{j.connector_name ?? "—"}</div>
                      <div className="text-[12px] text-charcoal-500">
                        {j.provider_id ?? ""}
                      </div>
                    </div>
                  ),
                },
                {
                  key: "trigger",
                  header: "Trigger",
                  render: (j) => <Badge variant="neutral">{j.trigger}</Badge>,
                },
                {
                  key: "status",
                  header: "Status",
                  render: (j) => (
                    <div className="min-w-[170px]">
                      <div className="flex items-center gap-2">
                        <StatusPill tone={syncStatusTone(j.status)}>
                          {SYNC_STATUS_LABEL[j.status]}
                        </StatusPill>
                        <span className="text-[11px] text-charcoal-500">
                          {j.progress_pct}%
                        </span>
                      </div>
                      <div className="mt-1.5">
                        <ProgressBar
                          value={j.progress_pct}
                          tone={syncProgressTone(j.status)}
                          ariaLabel="Sync progress"
                        />
                      </div>
                      {j.error_message && (
                        <div className="mt-1 text-[11px] text-status-red truncate max-w-[260px]">
                          {j.error_message}
                        </div>
                      )}
                    </div>
                  ),
                },
                {
                  key: "results",
                  header: "Results",
                  render: (j) => (
                    <span className="text-[12.5px] text-charcoal-700">
                      {syncStatsSummary(j.stats)}
                    </span>
                  ),
                },
                {
                  key: "started",
                  header: "Started",
                  render: (j) => (
                    <span className="text-[13px]">
                      {j.started_at ? formatDateTime(j.started_at) : "Queued"}
                    </span>
                  ),
                },
                {
                  key: "duration",
                  header: "Duration",
                  render: (j) => <span className="text-[13px]">{duration(j)}</span>,
                },
              ]}
              rows={filtered}
              emptyState={
                <div className="p-6 text-charcoal-500">
                  {jobs === null ? "Loading…" : "No jobs match the current filters."}
                </div>
              }
            />
          )}
        </CardBody>
      </Card>
    </div>
  );
}
