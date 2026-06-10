"use client";

import { useMemo, useState } from "react";
import { apiRequest, ApiError } from "@/lib/api";
import type { HumanOverride, OverrideType } from "@/lib/types";
import { hasCapability, useWorkspaceRole } from "@/lib/governance";
import { Button } from "@/components/ds/Button";
import { Input } from "@/components/ds/Input";
import { Select } from "@/components/ds/Select";
import { StatusPill } from "@/components/ds/StatusPill";
import { formatDateTime } from "@/lib/format";
import { ArrowRight } from "lucide-react";

interface FieldPreset {
  field: string;
  label: string;
  type: OverrideType;
}

/** Known override targets per module — the AI values humans most often adjust. */
const OVERRIDE_FIELDS: Record<string, FieldPreset[]> = {
  "capture.win_strategy": [
    { field: "win_confidence_assessment.score", label: "Win Confidence (%)", type: "score" },
    { field: "pursuit_recommendation", label: "Pursuit Recommendation", type: "decision" },
  ],
  "capture.bid_decision": [
    { field: "recommendation", label: "Bid Recommendation", type: "decision" },
    { field: "confidence.score", label: "Decision Confidence (%)", type: "score" },
  ],
  "capture.gate_review": [
    { field: "decision_recommendation", label: "Gate Recommendation", type: "decision" },
    { field: "probability_of_win.score", label: "Probability of Win (%)", type: "score" },
  ],
  "capture.executive_brief": [
    {
      field: "executive_recommendation.recommendation",
      label: "Executive Recommendation",
      type: "decision",
    },
    {
      field: "executive_recommendation.confidence_score",
      label: "Executive Confidence (%)",
      type: "score",
    },
  ],
};

function valueAtPath(obj: unknown, path: string): unknown {
  let cur: unknown = obj;
  for (const part of path.split(".")) {
    if (cur === null || typeof cur !== "object") return undefined;
    cur = (cur as Record<string, unknown>)[part];
  }
  return cur;
}

function renderValue(v: unknown): string {
  if (v === null || v === undefined) return "—";
  if (typeof v === "string") return v.replace(/_/g, " ");
  return String(v);
}

export function FeedbackPanel({
  opportunityId,
  moduleId,
  output,
  overrides,
  onChanged,
}: {
  opportunityId: string;
  moduleId: string;
  output: Record<string, unknown> | null;
  overrides: HumanOverride[];
  onChanged: () => Promise<void>;
}) {
  const role = useWorkspaceRole();
  const canOverride = hasCapability(role, "decision.override");
  const presets = OVERRIDE_FIELDS[moduleId] ?? [];

  const [open, setOpen] = useState(false);
  const [fieldIdx, setFieldIdx] = useState(0);
  const [customField, setCustomField] = useState("");
  const [customType, setCustomType] = useState<OverrideType>("score");
  const [overrideValue, setOverrideValue] = useState("");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const useCustom = presets.length === 0 || fieldIdx === presets.length;
  const preset = useCustom ? null : presets[fieldIdx];
  const field = preset ? preset.field : customField;
  const overrideType: OverrideType = preset ? preset.type : customType;
  const originalValue = useMemo(
    () => (output && field ? valueAtPath(output, field) : undefined),
    [output, field],
  );

  const moduleOverrides = overrides.filter((o) => o.module_id === moduleId);

  const submit = async () => {
    setBusy(true);
    setError(null);
    try {
      const parsed =
        overrideType === "score" && overrideValue.trim() !== "" && !Number.isNaN(Number(overrideValue))
          ? Number(overrideValue)
          : overrideValue.trim();
      await apiRequest(`/opportunities/${opportunityId}/overrides`, {
        method: "POST",
        body: {
          module_id: moduleId,
          override_type: overrideType,
          field,
          original_value: originalValue ?? null,
          override_value: parsed,
          reason: reason.trim(),
        },
      });
      setOpen(false);
      setOverrideValue("");
      setReason("");
      await onChanged();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Override failed.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <p className="text-[12px] text-charcoal-500">
        Overrides record human judgment alongside the AI recommendation — the
        original MissionIQ value is preserved, never overwritten.
      </p>

      {canOverride && !open && (
        <Button size="sm" variant="secondary" onClick={() => setOpen(true)} className="self-start">
          Record an Override
        </Button>
      )}

      {canOverride && open && (
        <div className="rounded-md border border-charcoal-100 bg-charcoal-100/30 p-3 flex flex-col gap-3">
          {presets.length > 0 ? (
            <Select
              label="Recommendation to override"
              value={String(fieldIdx)}
              onChange={(e) => setFieldIdx(Number(e.target.value))}
            >
              {presets.map((p, i) => (
                <option key={p.field} value={i}>
                  {p.label}
                </option>
              ))}
              <option value={presets.length}>Custom field…</option>
            </Select>
          ) : null}
          {useCustom && (
            <div className="grid grid-cols-2 gap-3">
              <Input
                label="Field path"
                value={customField}
                onChange={(e) => setCustomField(e.target.value)}
                placeholder="e.g. confidence.score"
              />
              <Select
                label="Type"
                value={customType}
                onChange={(e) => setCustomType(e.target.value as OverrideType)}
              >
                <option value="score">Score</option>
                <option value="decision">Decision</option>
              </Select>
            </div>
          )}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <div className="text-[13px] font-medium text-charcoal-700 mb-1.5">
                MissionIQ value
              </div>
              <div className="h-10 flex items-center rounded-[6px] border border-charcoal-100 bg-white px-3 text-[14px] text-charcoal-500">
                {renderValue(originalValue)}
              </div>
            </div>
            <Input
              label={overrideType === "score" ? "Your value" : "Your decision"}
              value={overrideValue}
              onChange={(e) => setOverrideValue(e.target.value)}
              placeholder={overrideType === "score" ? "e.g. 80" : "e.g. pursue_aggressively"}
            />
          </div>
          <Input
            label="Reason (required)"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="e.g. Strong executive relationship not reflected in data."
          />
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              onClick={submit}
              loading={busy}
              disabled={!field || !overrideValue.trim() || !reason.trim()}
            >
              Record Override
            </Button>
            <Button size="sm" variant="ghost" onClick={() => setOpen(false)}>
              Cancel
            </Button>
          </div>
          {error && <p className="text-[12px] text-status-red">{error}</p>}
        </div>
      )}

      {moduleOverrides.length === 0 ? (
        <p className="text-[13px] text-charcoal-500">
          No human overrides recorded for this briefing.
        </p>
      ) : (
        <ul className="flex flex-col gap-2">
          {moduleOverrides.map((o) => (
            <li key={o.id} className="rounded-md border border-charcoal-100 bg-white p-3">
              <div className="flex items-center justify-between gap-2">
                <span className="text-[12px] font-mono text-charcoal-700">{o.field}</span>
                <StatusPill tone={o.override_type === "decision" ? "info" : "amber"}>
                  {o.override_type === "decision" ? "Decision override" : "Score override"}
                </StatusPill>
              </div>
              <div className="mt-2 flex items-center gap-2 text-[13px]">
                <span className="rounded bg-charcoal-100 px-2 py-0.5 text-charcoal-700">
                  {renderValue(o.original_value)}
                </span>
                <ArrowRight className="h-3.5 w-3.5 text-charcoal-500" />
                <span className="rounded bg-steel-700/10 px-2 py-0.5 font-medium text-steel-700">
                  {renderValue(o.override_value)}
                </span>
              </div>
              <p className="mt-1.5 text-[12px] text-charcoal-700">{o.reason}</p>
              <p className="mt-1 text-[11px] text-charcoal-500">
                {o.created_by_name ?? "Unknown"} · {formatDateTime(o.created_at)}
              </p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
