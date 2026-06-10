"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Flag } from "lucide-react";
import { ApiError, apiRequest } from "@/lib/api";
import type { PursuitOutcome, PursuitOutcomeKind } from "@/lib/types";
import { OUTCOME_LABEL, OUTCOME_OPTIONS, outcomeTone } from "@/lib/outcomes";
import { formatCurrencyCents, formatDate } from "@/lib/format";
import { Button } from "@/components/ds/Button";
import { Card, CardBody, CardHeader } from "@/components/ds/Card";
import { Input } from "@/components/ds/Input";
import { Select } from "@/components/ds/Select";
import { StatusPill } from "@/components/ds/StatusPill";

/** Pursuit outcome capture — the terminal lifecycle event that feeds the
 *  Outcome Intelligence learning loop (graph weighting, win/loss patterns,
 *  recommendation performance). */
export function OutcomeCard({
  opportunityId,
  onChanged,
}: {
  opportunityId: string;
  onChanged?: () => void;
}) {
  const [outcome, setOutcome] = useState<PursuitOutcome | null | undefined>(
    undefined,
  );
  const [open, setOpen] = useState(false);

  const reload = useCallback(() => {
    apiRequest<PursuitOutcome>(`/opportunities/${opportunityId}/outcome`)
      .then(setOutcome)
      .catch(() => setOutcome(null));
  }, [opportunityId]);

  useEffect(reload, [reload]);

  if (outcome === undefined) return null;

  return (
    <>
      {outcome === null ? (
        <Card className="mb-6 border-charcoal-300/80">
          <CardBody>
            <div className="flex items-start gap-4">
              <div className="rounded-md bg-steel-700/10 text-steel-700 p-2">
                <Flag className="h-5 w-5" />
              </div>
              <div className="flex-1">
                <div className="miq-eyebrow">Outcome Intelligence · Improve</div>
                <h3 className="text-h3 text-charcoal-900 mt-1">
                  Record this pursuit&apos;s outcome
                </h3>
                <p className="text-[13.5px] text-charcoal-700 mt-1 max-w-2xl">
                  When this pursuit is decided, record the outcome. MissionIQ
                  updates Knowledge Graph track records, win/loss patterns, and
                  recommendation performance — every future pursuit gets smarter
                  for it.
                </p>
              </div>
              <Button variant="secondary" onClick={() => setOpen(true)}>
                Record Outcome
              </Button>
            </div>
          </CardBody>
        </Card>
      ) : (
        <Card className="mb-6">
          <CardHeader
            eyebrow="Outcome Intelligence · Recorded outcome"
            title="How this pursuit ended"
            actions={
              <div className="flex items-center gap-2">
                <Link href="/outcomes">
                  <Button size="sm" variant="secondary">
                    Open Outcome Intelligence
                  </Button>
                </Link>
                <Button size="sm" variant="secondary" onClick={() => setOpen(true)}>
                  Revise
                </Button>
              </div>
            }
          />
          <CardBody>
            <div className="flex flex-wrap items-center gap-x-5 gap-y-2">
              <StatusPill tone={outcomeTone(outcome.outcome)}>
                {OUTCOME_LABEL[outcome.outcome] ?? outcome.outcome}
              </StatusPill>
              {outcome.decided_at && (
                <span className="text-[13px] text-charcoal-700">
                  Decided {formatDate(outcome.decided_at)}
                </span>
              )}
              {outcome.awarded_value_cents != null && (
                <span className="miq-numeric text-[13px] text-charcoal-700">
                  {formatCurrencyCents(outcome.awarded_value_cents)}
                </span>
              )}
              {outcome.awarded_to_competitor && (
                <span className="text-[13px] text-charcoal-700">
                  Awarded to {outcome.awarded_to_competitor}
                </span>
              )}
            </div>
            {(outcome.outcome_factors?.length ?? 0) > 0 && (
              <div className="mt-3 flex flex-wrap gap-1.5">
                {outcome.outcome_factors!.map((f, i) => (
                  <span
                    key={i}
                    className="rounded bg-charcoal-100 px-2 py-0.5 text-[11.5px] text-charcoal-700"
                  >
                    {f}
                  </span>
                ))}
              </div>
            )}
            {outcome.debrief_notes && (
              <p className="mt-3 text-[13.5px] text-charcoal-700 whitespace-pre-wrap">
                {outcome.debrief_notes}
              </p>
            )}
            {outcome.recommendation_outcomes.length > 0 && (
              <p className="mt-3 text-[12px] text-charcoal-500">
                {outcome.recommendation_outcomes.length} MissionIQ
                recommendation(s) snapshotted against this outcome — alignment is
                tracked as a historical correlation on the Outcome Intelligence
                dashboard.
              </p>
            )}
          </CardBody>
        </Card>
      )}

      {open && (
        <RecordOutcomeModal
          opportunityId={opportunityId}
          existing={outcome}
          onClose={() => setOpen(false)}
          onSaved={() => {
            setOpen(false);
            reload();
            onChanged?.();
          }}
        />
      )}
    </>
  );
}

function RecordOutcomeModal({
  opportunityId,
  existing,
  onClose,
  onSaved,
}: {
  opportunityId: string;
  existing: PursuitOutcome | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [kind, setKind] = useState<PursuitOutcomeKind>(
    existing?.outcome ?? "won",
  );
  const [decidedAt, setDecidedAt] = useState(
    existing?.decided_at ? existing.decided_at.slice(0, 10) : "",
  );
  const [value, setValue] = useState(
    existing?.awarded_value_cents != null
      ? String(existing.awarded_value_cents / 100)
      : "",
  );
  const [competitor, setCompetitor] = useState(
    existing?.awarded_to_competitor ?? "",
  );
  const [factors, setFactors] = useState(
    (existing?.outcome_factors ?? []).join(", "),
  );
  const [notes, setNotes] = useState(existing?.debrief_notes ?? "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const save = async () => {
    setSaving(true);
    setError(null);
    try {
      const dollars = value.trim() ? Number(value.replace(/[$,]/g, "")) : null;
      await apiRequest(`/opportunities/${opportunityId}/outcome`, {
        method: "PUT",
        body: {
          outcome: kind,
          decided_at: decidedAt ? new Date(decidedAt).toISOString() : null,
          awarded_value_cents:
            dollars != null && !Number.isNaN(dollars)
              ? Math.round(dollars * 100)
              : null,
          awarded_to_competitor: competitor.trim() || null,
          outcome_factors: factors
            .split(",")
            .map((f) => f.trim())
            .filter(Boolean),
          debrief_notes: notes.trim() || null,
        },
      });
      onSaved();
    } catch (e) {
      setError(e instanceof ApiError ? e.detail : "Failed to record outcome.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-navy-900/40 p-4">
      <div className="w-full max-w-lg rounded-md bg-white shadow-elevated">
        <div className="border-b border-charcoal-300/60 px-5 py-4">
          <div className="miq-eyebrow">Outcome Intelligence</div>
          <div className="text-[16px] font-semibold text-charcoal-900">
            {existing ? "Revise pursuit outcome" : "Record pursuit outcome"}
          </div>
        </div>
        <div className="px-5 py-4 flex flex-col gap-4 max-h-[60vh] overflow-y-auto">
          <Select
            label="Outcome"
            value={kind}
            onChange={(e) => setKind(e.target.value as PursuitOutcomeKind)}
          >
            {OUTCOME_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </Select>
          <Input
            label="Decision date"
            type="date"
            value={decidedAt}
            onChange={(e) => setDecidedAt(e.target.value)}
          />
          <Input
            label="Award value (USD)"
            placeholder="e.g. 12500000"
            value={value}
            onChange={(e) => setValue(e.target.value)}
          />
          {kind === "lost" && (
            <Input
              label="Awarded to (competitor)"
              placeholder="Who won the award?"
              value={competitor}
              onChange={(e) => setCompetitor(e.target.value)}
            />
          )}
          <Input
            label="Outcome factors (comma-separated)"
            placeholder="e.g. price, transition approach, past performance"
            value={factors}
            onChange={(e) => setFactors(e.target.value)}
          />
          <div className="flex flex-col gap-1.5">
            <label
              htmlFor="debrief-notes"
              className="text-[13px] font-medium text-charcoal-700"
            >
              Debrief notes
            </label>
            <textarea
              id="debrief-notes"
              rows={3}
              className="rounded-[6px] border border-charcoal-300 bg-white px-3 py-2 text-[14px] text-charcoal-900 focus-visible:border-steel-500"
              placeholder="What the debrief or award notice said — recorded as supporting evidence."
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
            />
          </div>
          {error && (
            <div className="rounded-md p-3 text-status-red text-[13px] bg-status-redBg border border-status-red/30">
              {error}
            </div>
          )}
          <p className="text-[12px] text-charcoal-500">
            Recording an outcome moves the pursuit to its terminal stage,
            snapshots MissionIQ&apos;s recommendations for performance tracking,
            and updates Knowledge Graph track records. Everything is audited.
          </p>
        </div>
        <div className="flex justify-end gap-2 border-t border-charcoal-300/60 px-5 py-3">
          <Button variant="secondary" onClick={onClose} disabled={saving}>
            Cancel
          </Button>
          <Button onClick={save} loading={saving}>
            {existing ? "Save changes" : "Record outcome"}
          </Button>
        </div>
      </div>
    </div>
  );
}
