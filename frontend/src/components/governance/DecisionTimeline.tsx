"use client";

import { useEffect, useState } from "react";
import { apiRequest } from "@/lib/api";
import type { DecisionHistory, DecisionTimelineEntry } from "@/lib/types";
import { Card, CardBody, CardHeader } from "@/components/ds/Card";
import { formatDateTime } from "@/lib/format";
import {
  ArrowRight,
  CheckCircle2,
  FileText,
  Flag,
  PenLine,
  Send,
  ShieldCheck,
  ShieldX,
  XCircle,
} from "lucide-react";

function entryIcon(kind: DecisionTimelineEntry["kind"]): React.ReactNode {
  switch (kind) {
    case "generated":
      return <FileText className="h-3.5 w-3.5 text-steel-700" />;
    case "review_submitted":
      return <Send className="h-3.5 w-3.5 text-steel-700" />;
    case "review_approved":
      return <CheckCircle2 className="h-3.5 w-3.5 text-status-green" />;
    case "review_rejected":
      return <XCircle className="h-3.5 w-3.5 text-status-red" />;
    case "decision_overridden":
    case "score_overridden":
      return <PenLine className="h-3.5 w-3.5 text-status-amber" />;
    case "assumption_validated":
      return <ShieldCheck className="h-3.5 w-3.5 text-status-green" />;
    case "assumption_rejected":
      return <ShieldX className="h-3.5 w-3.5 text-status-red" />;
    case "outcome_recorded":
      return <Flag className="h-3.5 w-3.5 text-charcoal-900" />;
    default:
      return <FileText className="h-3.5 w-3.5 text-charcoal-500" />;
  }
}

function renderValue(v: unknown): string {
  if (v === null || v === undefined) return "—";
  if (typeof v === "string") return v.replace(/_/g, " ");
  return String(v);
}

/**
 * Pursuit-level decision ledger: generations, review transitions, human
 * overrides, assumption judgments, and the recorded outcome — AI originals
 * and human adjustments side by side, reconstructing every major decision.
 */
export function DecisionTimeline({ opportunityId }: { opportunityId: string }) {
  const [history, setHistory] = useState<DecisionHistory | null>(null);

  useEffect(() => {
    apiRequest<DecisionHistory>(`/opportunities/${opportunityId}/decision-history`)
      .then(setHistory)
      .catch(() => setHistory(null));
  }, [opportunityId]);

  const entries = history?.entries ?? [];
  if (entries.length === 0) return null;

  return (
    <Card>
      <CardHeader
        eyebrow="Collaboration & Governance"
        title="Decision History"
        subtitle="Every major decision on this pursuit, reconstructed in order — original MissionIQ recommendations and human adjustments preserved side by side."
      />
      <CardBody>
        <ul className="flex flex-col">
          {entries.map((e, i) => (
            <li key={`${e.kind}-${e.occurred_at}-${i}`} className="flex gap-3 pb-4 last:pb-0">
              <div className="flex flex-col items-center">
                {entryIcon(e.kind)}
                {i < entries.length - 1 && (
                  <div className="w-px flex-1 bg-charcoal-100 mt-1" />
                )}
              </div>
              <div className="min-w-0">
                <div className="flex flex-wrap items-baseline gap-x-2">
                  <span className="text-[13px] font-medium text-charcoal-900">
                    {e.label}
                  </span>
                  <span className="text-[12px] text-charcoal-500">
                    {formatDateTime(e.occurred_at)}
                  </span>
                  {e.actor_name && (
                    <span className="text-[12px] text-charcoal-500">
                      · {e.actor_name}
                    </span>
                  )}
                </div>
                {e.detail && (
                  <p className="mt-0.5 text-[12px] text-charcoal-700">{e.detail}</p>
                )}
                {(e.original_value !== null && e.original_value !== undefined) ||
                (e.adjusted_value !== null && e.adjusted_value !== undefined) ? (
                  <div className="mt-1.5 flex items-center gap-2 text-[12px]">
                    <span className="rounded bg-charcoal-100 px-2 py-0.5 text-charcoal-700">
                      {renderValue(e.original_value)}
                    </span>
                    <ArrowRight className="h-3 w-3 text-charcoal-500" />
                    <span className="rounded bg-steel-700/10 px-2 py-0.5 font-medium text-steel-700">
                      {renderValue(e.adjusted_value)}
                    </span>
                  </div>
                ) : null}
                {e.reason && (
                  <p className="mt-1 text-[12px] text-charcoal-500 italic">
                    “{e.reason}”
                  </p>
                )}
              </div>
            </li>
          ))}
        </ul>
      </CardBody>
    </Card>
  );
}
