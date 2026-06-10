"use client";

import type { DeliverableReview } from "@/lib/types";
import { REVIEW_STATUS_LABEL, reviewStatusTone } from "@/lib/governance";
import { StatusPill } from "@/components/ds/StatusPill";
import { formatDateTime } from "@/lib/format";
import { CheckCircle2, FileText, Send, XCircle, Archive, RotateCcw } from "lucide-react";

const EVENT_ICON: Record<string, React.ReactNode> = {
  submitted: <Send className="h-3.5 w-3.5 text-steel-700" />,
  approved: <CheckCircle2 className="h-3.5 w-3.5 text-status-green" />,
  rejected: <XCircle className="h-3.5 w-3.5 text-status-red" />,
  reopened: <RotateCcw className="h-3.5 w-3.5 text-charcoal-500" />,
  archived: <Archive className="h-3.5 w-3.5 text-charcoal-500" />,
};

/**
 * The immutable approval record: Generated → Submitted → Approved/Rejected,
 * with approver, date, and the decision snapshot — across every review cycle
 * (history is never overwritten).
 */
export function ApprovalPanel({ history }: { history: DeliverableReview[] }) {
  if (history.length === 0) {
    return (
      <p className="text-[13px] text-charcoal-500">
        No review cycles yet. Approvals appear here as immutable records once a
        review begins.
      </p>
    );
  }
  return (
    <div className="flex flex-col gap-4">
      {history.map((cycle, idx) => (
        <div key={cycle.id} className="rounded-md border border-charcoal-100 bg-white p-3">
          <div className="flex items-center justify-between gap-2">
            <span className="text-[12px] font-semibold text-charcoal-900">
              Review cycle {history.length - idx}
              {idx === 0 ? " (current)" : ""}
            </span>
            <StatusPill tone={reviewStatusTone(cycle.status)}>
              {REVIEW_STATUS_LABEL[cycle.status]}
            </StatusPill>
          </div>
          <ul className="mt-3 flex flex-col">
            {cycle.generated_at && (
              <li className="flex gap-2.5 pb-3">
                <div className="flex flex-col items-center">
                  <FileText className="h-3.5 w-3.5 text-charcoal-500" />
                  <div className="w-px flex-1 bg-charcoal-100 mt-1" />
                </div>
                <div className="text-[13px]">
                  <span className="font-medium text-charcoal-900">Generated</span>
                  <span className="ml-2 text-[12px] text-charcoal-500">
                    {formatDateTime(cycle.generated_at)}
                  </span>
                  <div className="text-[12px] text-charcoal-500">
                    MissionIQ generation — original intelligence preserved.
                  </div>
                </div>
              </li>
            )}
            {cycle.events.map((e, i) => (
              <li key={e.id} className="flex gap-2.5 pb-3 last:pb-0">
                <div className="flex flex-col items-center">
                  {EVENT_ICON[e.action] ?? EVENT_ICON.submitted}
                  {i < cycle.events.length - 1 && (
                    <div className="w-px flex-1 bg-charcoal-100 mt-1" />
                  )}
                </div>
                <div className="text-[13px]">
                  <span className="font-medium text-charcoal-900 capitalize">
                    {e.action}
                  </span>
                  <span className="ml-2 text-[12px] text-charcoal-500">
                    {formatDateTime(e.created_at)}
                  </span>
                  {e.actor_name && (
                    <div className="text-[12px] text-charcoal-500">
                      {e.action === "approved" ? "Approved by" : "By"} {e.actor_name}
                    </div>
                  )}
                  {e.decision_summary && (
                    <div className="text-[12px] text-charcoal-700">
                      Decision: <span className="font-medium">{e.decision_summary}</span>
                    </div>
                  )}
                  {e.notes && (
                    <p className="mt-0.5 text-[12px] text-charcoal-700 whitespace-pre-wrap">
                      {e.notes}
                    </p>
                  )}
                </div>
              </li>
            ))}
            {cycle.events.length === 0 && (
              <li className="text-[12px] text-charcoal-500">
                No review actions in this cycle yet.
              </li>
            )}
          </ul>
        </div>
      ))}
    </div>
  );
}
