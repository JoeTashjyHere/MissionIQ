"use client";

import { useState } from "react";
import { apiRequest, ApiError } from "@/lib/api";
import type { AssumptionItem, AssumptionPanelData } from "@/lib/types";
import { hasCapability, useWorkspaceRole } from "@/lib/governance";
import { Button } from "@/components/ds/Button";
import { StatusPill } from "@/components/ds/StatusPill";
import { formatDateTime } from "@/lib/format";

function statusTone(status: AssumptionItem["status"]): "green" | "red" | "neutral" {
  if (status === "validated") return "green";
  if (status === "rejected") return "red";
  return "neutral";
}

const STATUS_LABEL: Record<AssumptionItem["status"], string> = {
  unvalidated: "Unvalidated",
  validated: "Validated",
  rejected: "Rejected",
};

export function AssumptionsPanel({
  opportunityId,
  moduleId,
  panel,
  onChanged,
}: {
  opportunityId: string;
  moduleId: string;
  panel: AssumptionPanelData | null;
  onChanged: () => Promise<void>;
}) {
  const role = useWorkspaceRole();
  const canValidate = hasCapability(role, "assumption.validate");
  const [busyKey, setBusyKey] = useState<string | null>(null);
  const [notesFor, setNotesFor] = useState<string | null>(null);
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);

  if (!panel || panel.assumptions.length === 0) {
    return (
      <p className="text-[13px] text-charcoal-500">
        MissionIQ tagged no assumptions in this generation. Statements with an
        assumption basis appear here for human validation.
      </p>
    );
  }

  const judge = async (key: string, status: "validated" | "rejected") => {
    setBusyKey(key);
    setError(null);
    try {
      await apiRequest(
        `/opportunities/${opportunityId}/modules/${moduleId}/assumptions/validate`,
        { method: "POST", body: { key, status, notes: notes.trim() || null } },
      );
      setNotes("");
      setNotesFor(null);
      await onChanged();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Validation failed.");
    } finally {
      setBusyKey(null);
    }
  };

  return (
    <div className="flex flex-col gap-3">
      <p className="text-[12px] text-charcoal-500">
        The original AI-generated assumption always remains visible — human
        judgments are recorded alongside it, never over it.
      </p>
      {error && <p className="text-[12px] text-status-red">{error}</p>}
      {panel.assumptions.map((a) => (
        <div key={a.key} className="rounded-md border border-charcoal-100 bg-white p-3">
          <div className="flex items-start justify-between gap-3">
            <p className="text-[13px] text-charcoal-900">{a.text}</p>
            <StatusPill tone={statusTone(a.status)} className="shrink-0">
              {STATUS_LABEL[a.status]}
            </StatusPill>
          </div>
          <div className="mt-1 text-[11px] text-charcoal-500 font-mono">{a.path}</div>
          {a.latest && (
            <div className="mt-2 rounded bg-charcoal-100/40 px-2.5 py-1.5 text-[12px] text-charcoal-700">
              {a.latest.status === "validated" ? "Validated" : "Rejected"}
              {a.latest.validator_name ? ` by ${a.latest.validator_name}` : ""} ·{" "}
              {formatDateTime(a.latest.created_at)}
              {a.latest.notes && (
                <p className="mt-0.5 whitespace-pre-wrap">{a.latest.notes}</p>
              )}
            </div>
          )}
          {a.history.length > 1 && (
            <details className="mt-1.5">
              <summary className="cursor-pointer text-[11px] text-steel-700">
                {a.history.length - 1} earlier judgment
                {a.history.length - 1 === 1 ? "" : "s"}
              </summary>
              <ul className="mt-1 flex flex-col gap-1">
                {a.history.slice(0, -1).map((h) => (
                  <li key={h.id} className="text-[11px] text-charcoal-500">
                    {h.status} {h.validator_name ? `by ${h.validator_name}` : ""} ·{" "}
                    {formatDateTime(h.created_at)}
                    {h.notes ? ` — ${h.notes}` : ""}
                  </li>
                ))}
              </ul>
            </details>
          )}
          {canValidate && (
            <div className="mt-2.5 flex flex-col gap-2">
              {notesFor === a.key && (
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Validation notes (optional)…"
                  rows={2}
                  className="w-full rounded-[6px] border border-charcoal-300 bg-white px-3 py-2 text-[12px] text-charcoal-900 focus-visible:border-steel-500"
                />
              )}
              <div className="flex items-center gap-2">
                {notesFor !== a.key ? (
                  <button
                    onClick={() => {
                      setNotesFor(a.key);
                      setNotes("");
                    }}
                    className="text-[12px] font-medium text-steel-700 hover:text-charcoal-900"
                  >
                    {a.status === "unvalidated" ? "Validate or reject…" : "Re-judge…"}
                  </button>
                ) : (
                  <>
                    <Button
                      size="sm"
                      onClick={() => judge(a.key, "validated")}
                      loading={busyKey === a.key}
                    >
                      Validate
                    </Button>
                    <Button
                      size="sm"
                      variant="danger"
                      onClick={() => judge(a.key, "rejected")}
                      loading={busyKey === a.key}
                    >
                      Reject
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => setNotesFor(null)}
                    >
                      Cancel
                    </Button>
                  </>
                )}
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
