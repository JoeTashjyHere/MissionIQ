"use client";

import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { apiRequest, ApiError } from "@/lib/api";
import { PageHeader } from "@/components/PageHeader";
import { Card, CardBody, CardHeader } from "@/components/ds/Card";
import { DataTable } from "@/components/ds/DataTable";
import { Badge } from "@/components/ds/Badge";
import {
  hasCapability,
  ROLE_DESCRIPTIONS,
  ROLE_ORDER,
  useWorkspaceRole,
} from "@/lib/governance";
import type { Uuid, WorkspaceRole } from "@/lib/types";

interface TeamMember {
  id: Uuid;
  user_id: Uuid;
  workspace_id: Uuid;
  role: WorkspaceRole;
  user_email: string;
  user_full_name: string;
  joined_at: string | null;
  created_at: string;
}

export default function TeamPage() {
  const { currentWorkspaceId, user } = useAuth();
  const role = useWorkspaceRole();
  const canManage = hasCapability(role, "member.manage");
  const [members, setMembers] = useState<TeamMember[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(() => {
    if (!currentWorkspaceId) return;
    apiRequest<TeamMember[]>(`/workspaces/${currentWorkspaceId}/members`)
      .then(setMembers)
      .catch(() => setMembers([]));
  }, [currentWorkspaceId]);

  useEffect(reload, [reload]);

  const changeRole = async (member: TeamMember, newRole: WorkspaceRole) => {
    setError(null);
    try {
      await apiRequest(
        `/workspaces/${currentWorkspaceId}/members/${member.id}`,
        { method: "PATCH", body: { role: newRole } },
      );
      reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Failed to change role.");
    }
  };

  return (
    <div>
      <PageHeader
        eyebrow="MissionIQ · Workspace"
        title="Team members"
        subtitle="Workspace roles govern who can generate intelligence, review deliverables, approve decisions, and validate assumptions."
      />
      {error && (
        <div className="mb-4 rounded-md bg-status-redBg border border-status-red/30 text-status-red text-[13px] px-3 py-2">
          {error}
        </div>
      )}
      <Card>
        <CardHeader title="Members" />
        <CardBody className="!p-0">
          <DataTable
            columns={[
              { key: "name", header: "Name", render: (m) => <span className="font-medium">{m.user_full_name}</span> },
              { key: "email", header: "Email", render: (m) => <span className="font-mono text-[13px]">{m.user_email}</span> },
              {
                key: "role",
                header: "Role",
                render: (m) =>
                  canManage && m.user_id !== user?.id ? (
                    <select
                      value={m.role}
                      onChange={(e) => changeRole(m, e.target.value as WorkspaceRole)}
                      className="h-8 rounded-[6px] border border-charcoal-300 bg-white px-2 text-[12px] text-charcoal-900 capitalize"
                    >
                      {ROLE_ORDER.map((r) => (
                        <option key={r} value={r}>
                          {r}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <Badge className="capitalize">{m.role}</Badge>
                  ),
              },
            ]}
            rows={members ?? []}
            emptyState={
              <div className="p-6 text-charcoal-500">Loading…</div>
            }
          />
        </CardBody>
      </Card>
      <Card className="mt-6">
        <CardHeader
          eyebrow="Collaboration & Governance"
          title="Role capabilities"
          subtitle="Each role includes everything below it. Role changes are audited."
        />
        <CardBody>
          <dl className="flex flex-col gap-3">
            {ROLE_ORDER.map((r) => (
              <div key={r} className="flex items-start gap-3">
                <Badge className="capitalize mt-0.5 shrink-0 w-28 justify-center">{r}</Badge>
                <dd className="text-[13px] text-charcoal-700">{ROLE_DESCRIPTIONS[r]}</dd>
              </div>
            ))}
          </dl>
        </CardBody>
      </Card>
    </div>
  );
}
