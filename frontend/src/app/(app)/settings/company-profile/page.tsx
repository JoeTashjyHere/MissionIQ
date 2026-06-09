"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { apiRequest, ApiError } from "@/lib/api";
import type { Capability, CompanyProfile } from "@/lib/types";
import { PageHeader } from "@/components/PageHeader";
import { Card, CardBody, CardHeader } from "@/components/ds/Card";
import { Input, Textarea } from "@/components/ds/Input";
import { Button } from "@/components/ds/Button";
import { DataTable } from "@/components/ds/DataTable";
import { Badge } from "@/components/ds/Badge";

export default function CompanyProfilePage() {
  const { currentWorkspaceId } = useAuth();
  const [profile, setProfile] = useState<CompanyProfile | null>(null);
  const [caps, setCaps] = useState<Capability[]>([]);
  const [savedNotice, setSavedNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!currentWorkspaceId) return;
    Promise.all([
      apiRequest<CompanyProfile>(`/workspaces/${currentWorkspaceId}/company-profile`),
      apiRequest<Capability[]>(`/workspaces/${currentWorkspaceId}/capabilities`),
    ])
      .then(([p, c]) => {
        setProfile(p);
        setCaps(c);
      })
      .catch((e) => setError(e instanceof ApiError ? e.detail : "Failed to load."));
  }, [currentWorkspaceId]);

  const save = async () => {
    if (!profile || !currentWorkspaceId) return;
    setSaving(true);
    setSavedNotice(null);
    try {
      const updated = await apiRequest<CompanyProfile>(
        `/workspaces/${currentWorkspaceId}/company-profile`,
        { method: "PUT", body: profile },
      );
      setProfile(updated);
      setSavedNotice("Saved.");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Save failed.");
    } finally {
      setSaving(false);
    }
  };

  if (!profile) {
    return (
      <div>
        <PageHeader
          eyebrow="MissionIQ · Workspace"
          title="Company Profile"
          subtitle="Loading…"
        />
      </div>
    );
  }

  const update = (k: keyof CompanyProfile) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
      setProfile((p) => (p ? { ...p, [k]: e.target.value } : p));

  return (
    <div>
      <PageHeader
        eyebrow="MissionIQ · Workspace"
        title="Company Profile"
        subtitle="Used to ground capability-gap analysis and win-theme suggestions."
        actions={
          <Button onClick={save} loading={saving}>
            Save
          </Button>
        }
      />
      <div className="grid grid-cols-1 gap-6">
        <Card>
          <CardHeader title="Identity" />
          <CardBody>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Input
                label="Legal name"
                value={profile.legal_name ?? ""}
                onChange={update("legal_name")}
              />
              <Input
                label="Primary NAICS"
                value={profile.primary_naics ?? ""}
                onChange={update("primary_naics")}
              />
              <Input label="DUNS" value={profile.duns ?? ""} onChange={update("duns")} />
              <Input label="UEI" value={profile.uei ?? ""} onChange={update("uei")} />
              <Input
                label="CAGE Code"
                value={profile.cage_code ?? ""}
                onChange={update("cage_code")}
              />
              <Input
                label="Size standard"
                value={profile.size_standard ?? ""}
                onChange={update("size_standard")}
              />
            </div>
          </CardBody>
        </Card>
        <Card>
          <CardHeader title="Narrative" />
          <CardBody>
            <div className="flex flex-col gap-4">
              <Textarea
                label="Overview"
                value={profile.overview ?? ""}
                onChange={update("overview")}
              />
              <Textarea
                label="Differentiators"
                value={profile.differentiators ?? ""}
                onChange={update("differentiators")}
              />
              <Textarea
                label="Past performance summary"
                value={profile.past_performance_summary ?? ""}
                onChange={update("past_performance_summary")}
              />
            </div>
          </CardBody>
        </Card>
        <Card>
          <CardHeader title="Capabilities" subtitle="Used by Capability Gap Analysis." />
          <CardBody className="!p-0">
            <DataTable
              columns={[
                { key: "name", header: "Capability", render: (c) => <span className="font-medium">{c.name}</span> },
                { key: "category", header: "Category", render: (c) => c.category || "—" },
                {
                  key: "maturity",
                  header: "Maturity",
                  render: (c) => (c.maturity ? <Badge>{c.maturity}</Badge> : "—"),
                },
                { key: "desc", header: "Description", render: (c) => c.description || "—" },
              ]}
              rows={caps}
              emptyState={
                <div className="p-10 text-center text-charcoal-500">
                  No capabilities yet. Add capabilities via the API or seed script.
                </div>
              }
            />
          </CardBody>
        </Card>
      </div>
      {(savedNotice || error) && (
        <div className="fixed bottom-6 right-6 rounded-md px-4 py-2 text-[13px] shadow-elevated bg-white border">
          {savedNotice ?? error}
        </div>
      )}
    </div>
  );
}
