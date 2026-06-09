"use client";

import { PageHeader } from "@/components/PageHeader";
import { EmptyState } from "@/components/ds/EmptyState";
import { Globe2 } from "lucide-react";

export default function Page() {
  return (
    <div>
      <PageHeader
        eyebrow="Capture Intelligence · Market Intelligence"
        title="Saved records"
        subtitle="Records imported into this workspace from SAM.gov or licensed sources."
      />
      <EmptyState
        icon={<Globe2 />}
        title="No imported records yet"
        description="Use SAM.gov search to find opportunities, then import the ones relevant to your pursuits."
      />
    </div>
  );
}
