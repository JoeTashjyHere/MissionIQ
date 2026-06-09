"use client";

import { useCallback, useEffect, useState } from "react";
import { apiRequest, ApiError } from "@/lib/api";
import type { AIOutput } from "@/lib/types";
import { Card, CardBody, CardHeader } from "@/components/ds/Card";
import { Button } from "@/components/ds/Button";
import { EmptyState } from "@/components/ds/EmptyState";
import { CitationsRow } from "@/components/ds/Citation";
import { StatusPill } from "@/components/ds/StatusPill";
import { Skeleton } from "@/components/ds/Skeleton";
import { formatDateTime } from "@/lib/format";
import { Wand2 } from "lucide-react";

export function ModuleWorkbench({
  opportunityId,
  moduleId,
  moduleLabel,
  description,
  renderer,
}: {
  opportunityId: string;
  moduleId: string;
  moduleLabel: string;
  description: string;
  renderer: (output: Record<string, unknown>) => React.ReactNode;
}) {
  const [latest, setLatest] = useState<AIOutput | null | undefined>(undefined);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchLatest = useCallback(async () => {
    const r = await apiRequest<AIOutput | null>(
      `/opportunities/${opportunityId}/modules/${moduleId}/latest`,
    );
    setLatest(r ?? null);
  }, [opportunityId, moduleId]);

  useEffect(() => {
    fetchLatest().catch(() => setLatest(null));
  }, [fetchLatest]);

  const onRun = async () => {
    setRunning(true);
    setError(null);
    try {
      const out = await apiRequest<AIOutput>(
        `/opportunities/${opportunityId}/modules/${moduleId}/run`,
        { method: "POST", body: {} },
      );
      setLatest(out);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Generation failed.");
    } finally {
      setRunning(false);
    }
  };

  if (latest === undefined) {
    return (
      <div className="flex flex-col gap-3">
        <Skeleton className="h-10 w-1/2" />
        <Skeleton className="h-32" />
      </div>
    );
  }

  if (latest === null) {
    return (
      <EmptyState
        icon={<Wand2 />}
        title={`Generate ${moduleLabel}`}
        description={description}
        action={
          <Button onClick={onRun} loading={running}>
            Generate
          </Button>
        }
      />
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader
          eyebrow="MissionIQ Generation"
          title={moduleLabel}
          subtitle={`${latest.model_provider} · ${latest.model_name} · ${formatDateTime(latest.generated_at)}`}
          actions={
            <>
              <StatusPill
                tone={
                  latest.status === "ok"
                    ? "green"
                    : latest.status === "insufficient_context"
                      ? "amber"
                      : "red"
                }
              >
                {latest.status}
              </StatusPill>
              <Button variant="secondary" size="sm" onClick={onRun} loading={running}>
                Regenerate
              </Button>
            </>
          }
        />
        <CardBody>
          {latest.status === "insufficient_context" && (
            <div className="mb-4 rounded-md bg-status-amberBg border border-status-amber/30 text-status-amber text-[13px] px-3 py-2">
              We don&apos;t have enough source material to answer confidently.
              Upload additional documents (RFP, PWS, SOW, Sections L &amp; M)
              and regenerate.
            </div>
          )}
          {error && (
            <div className="mb-4 rounded-md bg-status-redBg border border-status-red/30 text-status-red text-[13px] px-3 py-2">
              {error}
            </div>
          )}
          {renderer(latest.output_json)}
          <div className="mt-6 border-t border-charcoal-100 pt-3">
            <CitationsRow citations={latest.citations} />
          </div>
        </CardBody>
      </Card>
    </div>
  );
}
