"use client";

import { useCallback, useEffect, useState } from "react";
import { Cable, Plug } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { ApiError, apiRequest } from "@/lib/api";
import type { Connector, ConnectorProviderSpec, ConnectorTestResult } from "@/lib/types";
import { CONNECTOR_STATUS_LABEL, connectorStatusTone } from "@/lib/integrations";
import { formatDateTime } from "@/lib/format";
import { PageHeader } from "@/components/PageHeader";
import { Badge } from "@/components/ds/Badge";
import { Button } from "@/components/ds/Button";
import { Card, CardBody, CardHeader } from "@/components/ds/Card";
import { DataTable } from "@/components/ds/DataTable";
import { EmptyState } from "@/components/ds/EmptyState";
import { Input } from "@/components/ds/Input";
import { StatusPill } from "@/components/ds/StatusPill";

const TYPE_LABEL: Record<string, string> = {
  crm: "CRM",
  document_repository: "Document Repository",
  market_intelligence: "Market Intelligence",
  project_management: "Project Management",
  knowledge_management: "Knowledge Management",
};

export default function ConnectorsPage() {
  const { currentWorkspaceId } = useAuth();
  const [providers, setProviders] = useState<ConnectorProviderSpec[] | null>(null);
  const [connectors, setConnectors] = useState<Connector[] | null>(null);
  const [adding, setAdding] = useState<ConnectorProviderSpec | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!currentWorkspaceId) return;
    const list = await apiRequest<Connector[]>(
      `/workspaces/${currentWorkspaceId}/connectors`,
    );
    setConnectors(list);
  }, [currentWorkspaceId]);

  useEffect(() => {
    if (!currentWorkspaceId) return;
    Promise.all([
      apiRequest<ConnectorProviderSpec[]>(`/connectors/providers`),
      apiRequest<Connector[]>(`/workspaces/${currentWorkspaceId}/connectors`),
    ])
      .then(([p, c]) => {
        setProviders(p);
        setConnectors(c);
      })
      .catch((e) => setError(e instanceof ApiError ? e.detail : "Failed to load."));
  }, [currentWorkspaceId]);

  const flash = (msg: string) => {
    setNotice(msg);
    setError(null);
    window.setTimeout(() => setNotice(null), 4000);
  };

  const action = async (connectorId: string, fn: () => Promise<void>) => {
    setBusyId(connectorId);
    try {
      await fn();
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Action failed.");
    } finally {
      setBusyId(null);
    }
  };

  const syncNow = (c: Connector) =>
    action(c.id, async () => {
      await apiRequest(`/workspaces/${currentWorkspaceId}/connectors/${c.id}/sync`, {
        method: "POST",
      });
      flash(`Sync started for ${c.name}. Track it in Sync History.`);
    });

  const testConnection = (c: Connector) =>
    action(c.id, async () => {
      const r = await apiRequest<ConnectorTestResult>(
        `/workspaces/${currentWorkspaceId}/connectors/${c.id}/test`,
        { method: "POST" },
      );
      flash(`${c.name}: ${r.message}`);
    });

  const toggleEnabled = (c: Connector) =>
    action(c.id, async () => {
      await apiRequest(`/workspaces/${currentWorkspaceId}/connectors/${c.id}`, {
        method: "PATCH",
        body: { enabled: c.status === "disabled" },
      });
      flash(c.status === "disabled" ? `${c.name} re-enabled.` : `${c.name} disabled.`);
    });

  const providerLabel = (id: string | null) =>
    providers?.find((p) => p.provider_id === id)?.label ?? id ?? "—";

  return (
    <div>
      <PageHeader
        eyebrow="MissionIQ · Integrations"
        title="Connectors"
        subtitle="Automated intelligence collection. Connect external systems and MissionIQ creates and populates pursuit workspaces with full data provenance."
      />

      <Card className="mb-6">
        <CardHeader
          title="Configured connectors"
          eyebrow="Workspace"
        />
        <CardBody className="!p-0">
          {error && (
            <div className="p-4 text-status-red text-[13px] bg-status-redBg border-b border-status-red/30">
              {error}
            </div>
          )}
          {connectors !== null && connectors.length === 0 ? (
            <div className="p-6">
              <EmptyState
                icon={<Plug />}
                title="No connectors configured"
                description="Add a connector below to start ingesting opportunities and documents automatically."
              />
            </div>
          ) : (
            <DataTable
              columns={[
                {
                  key: "name",
                  header: "Connector",
                  render: (c: Connector) => (
                    <div>
                      <div className="font-medium">{c.name}</div>
                      <div className="text-[12px] text-charcoal-500">
                        {providerLabel(c.provider_id)}
                      </div>
                    </div>
                  ),
                },
                {
                  key: "type",
                  header: "Type",
                  render: (c) => (
                    <Badge variant="neutral">
                      {TYPE_LABEL[c.connector_type] ?? c.connector_type}
                    </Badge>
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
                  key: "credential",
                  header: "Credential",
                  render: (c) =>
                    c.credential_type === "none" ? (
                      <span className="text-charcoal-500 text-[13px]">Not required</span>
                    ) : c.credential_set ? (
                      <Badge variant="teal">Set</Badge>
                    ) : (
                      <Badge>Missing</Badge>
                    ),
                },
                {
                  key: "automation",
                  header: "Automation",
                  render: (c) => (
                    <span className="text-[12px] text-charcoal-500">
                      {c.auto_create_pursuits ? "Create pursuits" : "Ingest only"}
                      {c.auto_run_automation ? " · Full automation" : ""}
                    </span>
                  ),
                },
                {
                  key: "last_sync",
                  header: "Last Sync",
                  render: (c) => (
                    <span className="text-[13px]">
                      {c.last_sync_at ? formatDateTime(c.last_sync_at) : "Never"}
                    </span>
                  ),
                },
                {
                  key: "actions",
                  header: "",
                  align: "right",
                  render: (c) => (
                    <div className="flex justify-end gap-2">
                      <Button
                        size="sm"
                        variant="secondary"
                        loading={busyId === c.id}
                        disabled={c.status === "disabled"}
                        onClick={() => syncNow(c)}
                      >
                        Sync now
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        loading={busyId === c.id}
                        onClick={() => testConnection(c)}
                      >
                        Test
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        loading={busyId === c.id}
                        onClick={() => toggleEnabled(c)}
                      >
                        {c.status === "disabled" ? "Enable" : "Disable"}
                      </Button>
                    </div>
                  ),
                },
              ]}
              rows={connectors ?? []}
              emptyState={<div className="p-6 text-charcoal-500">Loading…</div>}
            />
          )}
        </CardBody>
      </Card>

      <Card>
        <CardHeader
          title="Connector catalog"
          eyebrow="Available integrations"
        />
        <CardBody>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {(providers ?? []).map((p) => (
              <div
                key={p.provider_id}
                className="rounded-md border border-charcoal-300 bg-white p-4 flex flex-col gap-2"
              >
                <div className="flex items-center gap-2">
                  <Cable className="h-4 w-4 text-steel-700" />
                  <span className="font-semibold text-[14px]">{p.label}</span>
                  <span className="ml-auto flex items-center gap-1.5">
                    <Badge variant="neutral">
                      {TYPE_LABEL[p.connector_type] ?? p.connector_type}
                    </Badge>
                    {!p.implemented && (
                      <Badge variant="info">Planned · Phase {p.phase}</Badge>
                    )}
                  </span>
                </div>
                <p className="text-[12.5px] text-charcoal-500 leading-snug flex-1">
                  {p.description}
                </p>
                {p.requires_customer_authorization && (
                  <div className="text-[11px] font-medium uppercase tracking-wider text-status-amber">
                    Customer-authorized access only
                  </div>
                )}
                <div>
                  <Button
                    size="sm"
                    variant={p.implemented ? "primary" : "secondary"}
                    disabled={!p.implemented}
                    onClick={() => setAdding(p)}
                  >
                    {p.implemented ? "Configure" : "Coming soon"}
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </CardBody>
      </Card>

      {adding && currentWorkspaceId && (
        <AddConnectorForm
          provider={adding}
          workspaceId={currentWorkspaceId}
          onClose={() => setAdding(null)}
          onCreated={async () => {
            setAdding(null);
            flash("Connector created.");
            await refresh();
          }}
          onError={(msg) => setError(msg)}
        />
      )}

      {(notice || error) && (
        <div className="fixed bottom-6 right-6 rounded-md px-4 py-2 text-[13px] shadow-elevated bg-white border border-charcoal-300 max-w-md">
          {notice ?? error}
        </div>
      )}
    </div>
  );
}

function AddConnectorForm({
  provider,
  workspaceId,
  onClose,
  onCreated,
  onError,
}: {
  provider: ConnectorProviderSpec;
  workspaceId: string;
  onClose: () => void;
  onCreated: () => Promise<void>;
  onError: (msg: string) => void;
}) {
  const [name, setName] = useState(provider.label);
  const [config, setConfig] = useState<Record<string, string>>({});
  const [credential, setCredential] = useState("");
  const [autoCreate, setAutoCreate] = useState(true);
  const [autoRun, setAutoRun] = useState(false);
  const [saving, setSaving] = useState(false);

  const save = async () => {
    setSaving(true);
    try {
      await apiRequest(`/workspaces/${workspaceId}/connectors`, {
        method: "POST",
        body: {
          provider_id: provider.provider_id,
          name,
          config,
          credential: credential || null,
          auto_create_pursuits: autoCreate,
          auto_run_automation: autoRun,
        },
      });
      await onCreated();
    } catch (err) {
      onError(err instanceof ApiError ? err.detail : "Failed to create connector.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-navy-900/40 p-4">
      <div className="w-full max-w-lg rounded-md bg-white shadow-elevated">
        <div className="border-b border-charcoal-300/60 px-5 py-4">
          <div className="miq-eyebrow">Add connector</div>
          <div className="text-[16px] font-semibold text-charcoal-900">
            {provider.label}
          </div>
        </div>
        <div className="px-5 py-4 flex flex-col gap-4 max-h-[60vh] overflow-y-auto">
          <Input
            label="Connector name"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          {provider.config_fields.map((f) => (
            <Input
              key={f.key}
              label={f.label}
              placeholder={f.placeholder}
              required={f.required}
              value={config[f.key] ?? ""}
              onChange={(e) =>
                setConfig((prev) => ({ ...prev, [f.key]: e.target.value }))
              }
            />
          ))}
          {provider.auth_mode !== "none" && (
            <Input
              label={`Credential (${provider.auth_mode})`}
              type="password"
              placeholder="Stored encrypted; never displayed again"
              value={credential}
              onChange={(e) => setCredential(e.target.value)}
            />
          )}
          <label className="flex items-center gap-2 text-[13px] text-charcoal-700">
            <input
              type="checkbox"
              checked={autoCreate}
              onChange={(e) => setAutoCreate(e.target.checked)}
            />
            Automatically create pursuit workspaces from discovered opportunities
          </label>
          <label className="flex items-center gap-2 text-[13px] text-charcoal-700">
            <input
              type="checkbox"
              checked={autoRun}
              onChange={(e) => setAutoRun(e.target.checked)}
            />
            Run pursuit automation for new pursuits (Customer DNA → Executive
            Brief)
          </label>
        </div>
        <div className="flex justify-end gap-2 border-t border-charcoal-300/60 px-5 py-3">
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={save} loading={saving} disabled={!name.trim()}>
            Create connector
          </Button>
        </div>
      </div>
    </div>
  );
}
