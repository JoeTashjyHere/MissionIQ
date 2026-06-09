"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Activity, Workflow } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { ApiError, apiRequest } from "@/lib/api";
import type { AutomationRun, ConnectorHealthSummary } from "@/lib/types";
import {
  AUTOMATION_STATUS_LABEL,
  CONNECTOR_STATUS_LABEL,
  automationStatusTone,
  connectorStatusTone,
} from "@/lib/integrations";
import { formatDateTime } from "@/lib/format";
import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/ds/Button";
import { Card, CardBody, CardHeader } from "@/components/ds/Card";
import { DataTable } from "@/components/ds/DataTable";
import { EmptyState } from "@/components/ds/EmptyState";
import { KpiCard } from "@/components/ds/KpiCard";
import { StatusPill } from "@/components/ds/StatusPill";

const STEP_DOT: Record<string, string> = {
  succeeded: "bg-status-green",
  failed: "bg-status-red",
  running: "bg-status-amber animate-pulse",
  skipped: "bg-charcoal-300",
  pending: "bg-charcoal-100 border border-charcoal-300",
};

export default function ConnectorHealthPage() {
  const { currentWorkspaceId } = useAuth();
  const [health, setHealth] = useState<ConnectorHealthSummary | null>(null);
  const [runs, setRuns] = useState<AutomationRun[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [retryingId, setRetryingId] = useState<string | null>(null);

  useEffect(() => {
    if (!currentWorkspaceId) return;
    const refresh = () =>
      Promise.all([
        apiRequest<ConnectorHealthSummary>(
          `/workspaces/${currentWorkspaceId}/connectors/health`,
        ),
        apiRequest<AutomationRun[]>(
          `/workspaces/${currentWorkspaceId}/automation/runs?limit=25`,
        ),
      ])
        .then(([h, r]) => {
          setHealth(h);
          setRuns(r);
        })
        .catch((e) =>
          setError(e instanceof ApiError ? e.detail : "Failed to load health."),
        );
    refresh();
    const t = setInterval(refresh, 2500);
    return () => clearInterval(t);
  }, [currentWorkspaceId]);

  const retry = async (run: AutomationRun) => {
    setRetryingId(run.id);
    try {
      await apiRequest(
        `/workspaces/${currentWorkspaceId}/automation/runs/${run.id}/retry`,
        { method: "POST" },
      );
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Retry failed.");
    } finally {
      setRetryingId(null);
    }
  };

  return (
    <div>
      <PageHeader
        eyebrow="MissionIQ · Integrations"
        title="Connector Health"
        subtitle="Live operational status across connectors, sync jobs, and pursuit automation runs."
      />

      {error && (
        <div className="mb-4 rounded-md p-4 text-status-red text-[13px] bg-status-redBg border border-status-red/30">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <KpiCard
          label="Connectors Connected"
          value={health ? `${health.connected}/${health.total}` : "—"}
          helper="Healthy integrations"
        />
        <KpiCard
          label="Failing Connectors"
          value={health?.failed ?? "—"}
          tone={health && health.failed > 0 ? "red" : undefined}
          helper="Require attention"
        />
        <KpiCard
          label="Sync Jobs (24h)"
          value={health?.jobs_24h ?? "—"}
          tone={health && health.failed_jobs_24h > 0 ? "amber" : undefined}
          helper={
            health && health.failed_jobs_24h > 0
              ? `${health.failed_jobs_24h} failed`
              : "All clear"
          }
        />
        <KpiCard
          label="Automation Runs (24h)"
          value={health?.automation_runs_24h ?? "—"}
          helper="Pursuit workspaces automated"
        />
      </div>

      <Card className="mb-6">
        <CardHeader title="Connector status" eyebrow="Per connector" />
        <CardBody className="!p-0">
          {health !== null && health.connectors.length === 0 ? (
            <div className="p-6">
              <EmptyState
                icon={<Activity />}
                title="No connectors configured"
                description="Add a connector to start monitoring its health here."
              />
            </div>
          ) : (
            <DataTable
              columns={[
                {
                  key: "name",
                  header: "Connector",
                  render: (c) => (
                    <div>
                      <div className="font-medium">{c.name}</div>
                      <div className="text-[12px] text-charcoal-500">{c.provider_id}</div>
                    </div>
                  ),
                },
                {
                  key: "status",
                  header: "State",
                  render: (c) => (
                    <StatusPill tone={connectorStatusTone(c.status)}>
                      {CONNECTOR_STATUS_LABEL[c.status]}
                    </StatusPill>
                  ),
                },
                {
                  key: "failures",
                  header: "Consecutive Failures",
                  render: (c) => (
                    <span
                      className={
                        c.consecutive_failures > 0
                          ? "text-status-red font-medium"
                          : "text-charcoal-500"
                      }
                    >
                      {c.consecutive_failures}
                    </span>
                  ),
                },
                {
                  key: "last_success",
                  header: "Last Successful Sync",
                  render: (c) => (
                    <span className="text-[13px]">
                      {c.last_success_at ? formatDateTime(c.last_success_at) : "Never"}
                    </span>
                  ),
                },
              ]}
              rows={health?.connectors ?? []}
              emptyState={<div className="p-6 text-charcoal-500">Loading…</div>}
            />
          )}
        </CardBody>
      </Card>

      <Card>
        <CardHeader
          title="Pursuit automation runs"
          eyebrow="Opportunity Created → Executive Brief"
          subtitle="Each run executes the automation step plan with retries, partial-failure handling, and a full audit trail."
        />
        <CardBody className="!p-0">
          {runs !== null && runs.length === 0 ? (
            <div className="p-6">
              <EmptyState
                icon={<Workflow />}
                title="No automation runs yet"
                description="Runs start automatically from connector syncs (when enabled) or manually from a pursuit workspace."
              />
            </div>
          ) : (
            <DataTable
              columns={[
                {
                  key: "pursuit",
                  header: "Pursuit",
                  render: (r: AutomationRun) => (
                    <Link
                      href={`/capture/opportunities/${r.opportunity_id}`}
                      className="font-medium text-steel-700 hover:underline"
                    >
                      {r.opportunity_name ?? "View pursuit"}
                    </Link>
                  ),
                },
                {
                  key: "status",
                  header: "Status",
                  render: (r) => (
                    <StatusPill tone={automationStatusTone(r.status)}>
                      {AUTOMATION_STATUS_LABEL[r.status]}
                    </StatusPill>
                  ),
                },
                {
                  key: "steps",
                  header: "Steps",
                  render: (r) => (
                    <div className="flex items-center gap-1.5">
                      {r.steps.map((s) => (
                        <span
                          key={s.step_id}
                          title={`${s.label}: ${s.status}${s.error ? ` — ${s.error}` : ""}`}
                          className={`h-2.5 w-2.5 rounded-full ${STEP_DOT[s.status] ?? STEP_DOT.pending}`}
                        />
                      ))}
                      {r.current_step && (
                        <span className="ml-1 text-[11px] text-charcoal-500">
                          {r.current_step.replaceAll("_", " ")}
                        </span>
                      )}
                    </div>
                  ),
                },
                {
                  key: "trigger",
                  header: "Trigger",
                  render: (r) => (
                    <span className="text-[12px] text-charcoal-500 capitalize">
                      {r.trigger}
                    </span>
                  ),
                },
                {
                  key: "started",
                  header: "Started",
                  render: (r) => (
                    <span className="text-[13px]">
                      {r.started_at ? formatDateTime(r.started_at) : "Queued"}
                    </span>
                  ),
                },
                {
                  key: "actions",
                  header: "",
                  align: "right",
                  render: (r) =>
                    r.status === "failed" || r.status === "partial" ? (
                      <Button
                        size="sm"
                        variant="secondary"
                        loading={retryingId === r.id}
                        onClick={() => retry(r)}
                      >
                        Retry failed steps
                      </Button>
                    ) : null,
                },
              ]}
              rows={runs ?? []}
              emptyState={<div className="p-6 text-charcoal-500">Loading…</div>}
            />
          )}
        </CardBody>
      </Card>
    </div>
  );
}
