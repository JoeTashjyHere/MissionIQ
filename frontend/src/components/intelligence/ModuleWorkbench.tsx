"use client";

import { useCallback, useEffect, useState } from "react";
import { apiRequest, ApiError } from "@/lib/api";
import type { AIOutput, DocumentRecord } from "@/lib/types";
import { Card, CardBody, CardHeader } from "@/components/ds/Card";
import { Button } from "@/components/ds/Button";
import { EmptyState } from "@/components/ds/EmptyState";
import { CitationsRow } from "@/components/ds/Citation";
import { StatusPill } from "@/components/ds/StatusPill";
import { Skeleton } from "@/components/ds/Skeleton";
import { formatDateTime } from "@/lib/format";
import { AlertTriangle, FileWarning, Wand2 } from "lucide-react";

type Renderer = (output: Record<string, unknown>) => React.ReactNode;
type OutputRenderer = (output: AIOutput) => React.ReactNode;

export function ModuleWorkbench({
  opportunityId,
  moduleId,
  moduleLabel,
  description,
  renderer,
  outputRenderer,
}: {
  opportunityId: string;
  moduleId: string;
  moduleLabel: string;
  description: string;
  /** Legacy: receives just output_json. Prefer `outputRenderer`. */
  renderer?: Renderer;
  /** New: receives the full AIOutput (citations, status, model, etc.) */
  outputRenderer?: OutputRenderer;
}) {
  const [latest, setLatest] = useState<AIOutput | null | undefined>(undefined);
  const [docs, setDocs] = useState<DocumentRecord[] | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchLatest = useCallback(async () => {
    const r = await apiRequest<AIOutput | null>(
      `/opportunities/${opportunityId}/modules/${moduleId}/latest`,
    );
    setLatest(r ?? null);
  }, [opportunityId, moduleId]);

  const fetchDocs = useCallback(async () => {
    const r = await apiRequest<DocumentRecord[]>(
      `/opportunities/${opportunityId}/documents`,
    );
    setDocs(r);
  }, [opportunityId]);

  useEffect(() => {
    fetchLatest().catch(() => setLatest(null));
    fetchDocs().catch(() => setDocs([]));
  }, [fetchLatest, fetchDocs]);

  const readyDocs = (docs ?? []).filter((d) => d.status === "ready");
  const processingDocs = (docs ?? []).filter(
    (d) => d.status !== "ready" && d.status !== "failed",
  );

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

  if (latest === undefined || docs === null) {
    return (
      <div className="flex flex-col gap-3">
        <Skeleton className="h-10 w-1/2" />
        <Skeleton className="h-32" />
        <Skeleton className="h-32" />
      </div>
    );
  }

  const noReadyDocs = readyDocs.length === 0;

  if (latest === null) {
    if (noReadyDocs) {
      return (
        <EmptyState
          icon={<FileWarning />}
          title="No indexed documents yet"
          description={
            processingDocs.length > 0
              ? `${processingDocs.length} document(s) are still being processed. Once they reach the "ready" state you can generate ${moduleLabel.toLowerCase()}.`
              : `Upload an RFP, PWS, or Sections L & M on the Documents tab. ${moduleLabel} grounds every finding in source material — without documents, MissionIQ will not attempt analysis.`
          }
        />
      );
    }
    return (
      <EmptyState
        icon={<Wand2 />}
        title={`Generate ${moduleLabel}`}
        description={description}
        action={
          <Button onClick={onRun} loading={running}>
            Generate {moduleLabel}
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
                {latest.status === "ok"
                  ? "Grounded"
                  : latest.status === "insufficient_context"
                    ? "Insufficient context"
                    : "Error"}
              </StatusPill>
              <Button
                variant="secondary"
                size="sm"
                onClick={onRun}
                loading={running}
                disabled={noReadyDocs}
                title={
                  noReadyDocs
                    ? "Upload and index at least one document before regenerating."
                    : undefined
                }
              >
                Regenerate
              </Button>
            </>
          }
        />
        <CardBody>
          {latest.status === "insufficient_context" && (
            <div className="mb-4 rounded-md bg-status-amberBg border border-status-amber/30 text-status-amber text-[13px] px-3 py-2 flex items-start gap-2">
              <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
              <div>
                MissionIQ could not produce a confident briefing from the
                indexed material. Upload additional documents (RFP, PWS, SOW,
                Sections L &amp; M) and regenerate.
              </div>
            </div>
          )}
          {latest.status === "error" && (
            <div className="mb-4 rounded-md bg-status-redBg border border-status-red/30 text-status-red text-[13px] px-3 py-2">
              The model returned an unparsable response. Click Regenerate to
              retry, or contact your administrator if the issue persists.
            </div>
          )}
          {error && (
            <div className="mb-4 rounded-md bg-status-redBg border border-status-red/30 text-status-red text-[13px] px-3 py-2">
              {error}
            </div>
          )}
          {outputRenderer
            ? outputRenderer(latest)
            : renderer
              ? renderer(latest.output_json)
              : null}
          <div className="mt-6 border-t border-charcoal-100 pt-3">
            <CitationsRow citations={latest.citations} />
          </div>
        </CardBody>
      </Card>
    </div>
  );
}
