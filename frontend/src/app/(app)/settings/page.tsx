"use client";

import { useAuth } from "@/lib/auth-context";
import { PageHeader } from "@/components/PageHeader";
import { Card, CardBody, CardHeader } from "@/components/ds/Card";
import { Badge } from "@/components/ds/Badge";

export default function SettingsPage() {
  const { user, memberships, currentWorkspaceId } = useAuth();
  const current = memberships.find((m) => m.workspace_id === currentWorkspaceId);
  return (
    <div>
      <PageHeader
        eyebrow="MissionIQ · Workspace"
        title="Settings"
        subtitle="Workspace identity, account, and platform info."
      />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader title="Account" />
          <CardBody>
            <dl className="grid grid-cols-2 gap-y-3 text-[14px]">
              <dt className="text-charcoal-500">Full name</dt>
              <dd>{user?.full_name}</dd>
              <dt className="text-charcoal-500">Email</dt>
              <dd className="font-mono text-[13px]">{user?.email}</dd>
              <dt className="text-charcoal-500">Account status</dt>
              <dd>
                <Badge variant="teal">{user?.is_active ? "Active" : "Inactive"}</Badge>
              </dd>
            </dl>
          </CardBody>
        </Card>
        <Card>
          <CardHeader title="Workspace" />
          <CardBody>
            <dl className="grid grid-cols-2 gap-y-3 text-[14px]">
              <dt className="text-charcoal-500">Name</dt>
              <dd>{current?.workspace_name ?? "—"}</dd>
              <dt className="text-charcoal-500">Slug</dt>
              <dd className="font-mono text-[13px]">
                {current?.workspace_slug ?? "—"}
              </dd>
              <dt className="text-charcoal-500">Your role</dt>
              <dd>
                <Badge>{current?.role ?? "—"}</Badge>
              </dd>
            </dl>
          </CardBody>
        </Card>
      </div>
    </div>
  );
}
