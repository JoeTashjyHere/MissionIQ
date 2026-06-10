"use client";

import { useState } from "react";
import { apiRequest, ApiError } from "@/lib/api";
import type { DeliverableReview, ReviewAction } from "@/lib/types";
import {
  hasCapability,
  REVIEW_STATUS_LABEL,
  reviewStatusTone,
  useWorkspaceRole,
} from "@/lib/governance";
import { Button } from "@/components/ds/Button";
import { StatusPill } from "@/components/ds/StatusPill";
import { formatDateTime } from "@/lib/format";

const EVENT_LABEL: Record<string, string> = {
  submitted: "Submitted for review",
  approved: "Approved",
  rejected: "Rejected",
  reopened: "Reopened",
  archived: "Archived",
};

export function ReviewPanel({
  opportunityId,
  moduleId,
  review,
  onChanged,
}: {
  opportunityId: string;
  moduleId: string;
  review: DeliverableReview | null;
  onChanged: () => Promise<void>;
}) {
  const role = useWorkspaceRole();
  const canSubmit = hasCapability(role, "review.submit");
  const canDecide = hasCapability(role, "review.decide");
  const [busy, setBusy] = useState(false);
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);

  if (review === null) {
    return (
      <p className="text-[13px] text-charcoal-500">
        Generate this deliverable to start a review cycle.
      </p>
    );
  }

  const act = async (action: ReviewAction) => {
    setBusy(true);
    setError(null);
    try {
      await apiRequest(
        `/opportunities/${opportunityId}/modules/${moduleId}/review`,
        { method: "POST", body: { action, notes: notes.trim() || null } },
      );
      setNotes("");
      await onChanged();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Review action failed.");
    } finally {
      setBusy(false);
    }
  };

  const decisionNotesMissing = !notes.trim();

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <StatusPill tone={reviewStatusTone(review.status)}>
            {REVIEW_STATUS_LABEL[review.status]}
          </StatusPill>
          {review.generated_at && (
            <span className="text-[12px] text-charcoal-500">
              Reviewing generation of {formatDateTime(review.generated_at)}
            </span>
          )}
        </div>
      </div>

      {(canSubmit || canDecide) && review.status !== "archived" && (
        <div className="rounded-md border border-charcoal-100 bg-charcoal-100/30 p-3 flex flex-col gap-2">
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder={
              review.status === "in_review"
                ? "Review notes (required to approve or reject)…"
                : "Notes (optional)…"
            }
            rows={2}
            className="w-full rounded-[6px] border border-charcoal-300 bg-white px-3 py-2 text-[13px] text-charcoal-900 focus-visible:border-steel-500"
          />
          <div className="flex flex-wrap items-center gap-2">
            {canSubmit && (review.status === "draft" || review.status === "rejected") && (
              <Button size="sm" onClick={() => act("submit")} loading={busy}>
                Submit for Review
              </Button>
            )}
            {canDecide && review.status === "in_review" && (
              <>
                <Button
                  size="sm"
                  onClick={() => act("approve")}
                  loading={busy}
                  disabled={decisionNotesMissing}
                  title={decisionNotesMissing ? "Review notes are required." : undefined}
                >
                  Approve
                </Button>
                <Button
                  size="sm"
                  variant="danger"
                  onClick={() => act("reject")}
                  loading={busy}
                  disabled={decisionNotesMissing}
                  title={decisionNotesMissing ? "Review notes are required." : undefined}
                >
                  Reject
                </Button>
              </>
            )}
            {canDecide &&
              (review.status === "approved" || review.status === "rejected") && (
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => act("reopen")}
                  loading={busy}
                >
                  Reopen Review
                </Button>
              )}
          </div>
          {!canDecide && review.status === "in_review" && (
            <p className="text-[12px] text-charcoal-500">
              Awaiting an approver decision. Your role can comment and submit, but
              approving or rejecting requires the approver role.
            </p>
          )}
          {error && <p className="text-[12px] text-status-red">{error}</p>}
        </div>
      )}

      <div>
        <div className="text-[11px] font-semibold uppercase tracking-wide text-charcoal-500 mb-2">
          Review history — preserved, never overwritten
        </div>
        {review.events.length === 0 ? (
          <p className="text-[13px] text-charcoal-500">
            No review actions yet for this generation.
          </p>
        ) : (
          <ul className="flex flex-col gap-2">
            {review.events.map((e) => (
              <li
                key={e.id}
                className="rounded-md border border-charcoal-100 bg-white px-3 py-2 text-[13px]"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="font-medium text-charcoal-900">
                    {EVENT_LABEL[e.action] ?? e.action}
                  </span>
                  <span className="text-[12px] text-charcoal-500">
                    {formatDateTime(e.created_at)}
                  </span>
                </div>
                {(e.actor_name || e.decision_summary) && (
                  <div className="mt-0.5 text-[12px] text-charcoal-500">
                    {e.actor_name && <span>By {e.actor_name}</span>}
                    {e.actor_name && e.decision_summary && <span> · </span>}
                    {e.decision_summary && (
                      <span>Decision: {e.decision_summary}</span>
                    )}
                  </div>
                )}
                {e.notes && (
                  <p className="mt-1 text-[12px] text-charcoal-700 whitespace-pre-wrap">
                    {e.notes}
                  </p>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
