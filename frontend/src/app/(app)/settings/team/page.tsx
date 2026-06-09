"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { apiRequest } from "@/lib/api";
import { PageHeader } from "@/components/PageHeader";
import { Card, CardBody, CardHeader } from "@/components/ds/Card";
import { DataTable } from "@/components/ds/DataTable";
import { Badge } from "@/components/ds/Badge";
import type { Uuid } from "@/lib/types";

interface TeamMember {
  id: Uuid;
  user_id: Uuid;
  workspace_id: Uuid;
  role: string;
  user_email: string;
  user_full_name: string;
  joined_at: string | null;
  created_at: string;
}

export default function TeamPage() {
  const { currentWorkspaceId } = useAuth();
  const [members, setMembers] = useState<TeamMember[] | null>(null);

  useEffect(() => {
    if (!currentWorkspaceId) return;
    apiRequest<TeamMember[]>(`/workspaces/${currentWorkspaceId}/members`)
      .then(setMembers)
      .catch(() => setMembers([]));
  }, [currentWorkspaceId]);

  return (
    <div>
      <PageHeader
        eyebrow="MissionIQ · Workspace"
        title="Team members"
        subtitle="Members of this workspace and their roles."
      />
      <Card>
        <CardHeader title="Members" />
        <CardBody className="!p-0">
          <DataTable
            columns={[
              { key: "name", header: "Name", render: (m) => <span className="font-medium">{m.user_full_name}</span> },
              { key: "email", header: "Email", render: (m) => <span className="font-mono text-[13px]">{m.user_email}</span> },
              { key: "role", header: "Role", render: (m) => <Badge>{m.role}</Badge> },
            ]}
            rows={members ?? []}
            emptyState={
              <div className="p-6 text-charcoal-500">Loading…</div>
            }
          />
        </CardBody>
      </Card>
    </div>
  );
}
