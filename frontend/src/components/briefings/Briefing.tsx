/**
 * Briefing design system — boardroom-ready, consulting-grade building blocks.
 *
 * Every component is a self-contained, slide-mappable section so the briefing
 * pages can later be exported to PowerPoint / PDF / Word with a 1:1 section →
 * slide mapping. Components are presentational (props in, layout out).
 */
import type {
  BriefRisk,
  CaptureAction,
  Confidence,
  HistoricalEvidence,
  ScoreBlock,
  StrategicBasis,
  StrategicPoint,
} from "@/lib/types";
import { StatusPill } from "@/components/ds/StatusPill";

// ── Epistemic honesty: Evidence / Inference / Assumption ───────────────────

const BASIS_STYLE: Record<StrategicBasis, { label: string; cls: string }> = {
  evidence: { label: "Evidence", cls: "bg-status-greenBg text-status-green" },
  inference: { label: "Inference", cls: "bg-steel-700/10 text-steel-700" },
  assumption: { label: "Assumption", cls: "bg-status-amberBg text-status-amber" },
};

export function BasisChip({ basis }: { basis?: StrategicBasis }) {
  const s = BASIS_STYLE[basis ?? "inference"];
  return (
    <span
      className={`inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${s.cls}`}
    >
      {s.label}
    </span>
  );
}

export function BasisLegend() {
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 text-[12px] text-charcoal-600">
      <span className="font-medium text-charcoal-700">How to read this:</span>
      <span className="inline-flex items-center gap-1.5">
        <BasisChip basis="evidence" /> what MissionIQ knows
      </span>
      <span className="inline-flex items-center gap-1.5">
        <BasisChip basis="inference" /> what MissionIQ believes
      </span>
      <span className="inline-flex items-center gap-1.5">
        <BasisChip basis="assumption" /> what needs validating
      </span>
      <span className="inline-flex items-center gap-1.5">
        <span className="inline-flex items-center rounded bg-navy-700/10 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-navy-700">
          Historical
        </span>
        recalled from prior pursuits
      </span>
    </div>
  );
}

export function Sources({ sources }: { sources?: string[] }) {
  if (!sources?.length) return null;
  return (
    <div className="mt-1 flex flex-wrap gap-1">
      {sources.map((s, i) => (
        <span
          key={i}
          className="rounded bg-charcoal-100 px-1.5 py-0.5 text-[10px] font-mono text-charcoal-600"
        >
          {s}
        </span>
      ))}
    </div>
  );
}

export function PointList({
  points,
  empty = "None identified.",
  tone = "neutral",
}: {
  points?: StrategicPoint[];
  empty?: string;
  tone?: "neutral" | "positive" | "negative";
}) {
  if (!points?.length) {
    return <p className="text-charcoal-500 italic text-[13px]">{empty}</p>;
  }
  const border =
    tone === "positive"
      ? "border-status-green/25"
      : tone === "negative"
        ? "border-status-red/25"
        : "border-charcoal-200";
  return (
    <ul className="flex flex-col gap-2">
      {points.map((p, i) => (
        <li key={i} className={`rounded-md border ${border} px-3 py-2`}>
          <div className="flex items-start justify-between gap-3">
            <p className="text-[13.5px] text-charcoal-900 leading-relaxed">
              {p.statement}
            </p>
            <BasisChip basis={p.basis} />
          </div>
          <Sources sources={p.sources} />
        </li>
      ))}
    </ul>
  );
}

// ── Confidence gauge ───────────────────────────────────────────────────────

function gaugeColor(level?: string) {
  return level === "high"
    ? "bg-status-green"
    : level === "low"
      ? "bg-status-red"
      : "bg-status-amber";
}

export function ConfidenceGauge({
  score,
  level,
  label = "Win confidence",
}: {
  score: number;
  level?: string;
  label?: string;
}) {
  const pct = Math.max(0, Math.min(100, score));
  return (
    <div className="w-full sm:w-64">
      <div className="flex items-baseline justify-between">
        <span className="miq-eyebrow">{label}</span>
        <span className="miq-numeric text-[26px] font-semibold leading-none text-charcoal-900">
          {pct}
          <span className="text-[14px] text-charcoal-500">%</span>
        </span>
      </div>
      <div className="mt-2 h-2 w-full rounded-full bg-charcoal-100">
        <div
          className={`h-2 rounded-full ${gaugeColor(level)}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

// ── Score bar (gate review) ────────────────────────────────────────────────

function scoreTone(score: number, invert = false): "green" | "amber" | "red" {
  const s = invert ? 100 - score : score;
  if (s >= 67) return "green";
  if (s >= 40) return "amber";
  return "red";
}

const TONE_BAR: Record<string, string> = {
  green: "bg-status-green",
  amber: "bg-status-amber",
  red: "bg-status-red",
};

export function ScoreBar({
  label,
  block,
  invert = false,
}: {
  label: string;
  block: ScoreBlock;
  /** When true (e.g. Risk), a HIGHER score is worse, so tone is flipped. */
  invert?: boolean;
}) {
  const pct = Math.max(0, Math.min(100, block.score));
  const tone = scoreTone(pct, invert);
  return (
    <div className="rounded-md border border-charcoal-200 px-3.5 py-3">
      <div className="flex items-center justify-between gap-3">
        <span className="text-[13px] font-semibold text-charcoal-900">
          {label}
        </span>
        <div className="flex items-center gap-2">
          <BasisChip basis={block.basis} />
          <span className="miq-numeric text-[18px] font-semibold text-charcoal-900">
            {pct}
            <span className="text-[11px] text-charcoal-500">/100</span>
          </span>
        </div>
      </div>
      <div className="mt-2 h-2 w-full rounded-full bg-charcoal-100">
        <div
          className={`h-2 rounded-full ${TONE_BAR[tone]}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      {block.rationale && (
        <p className="mt-2 text-[12.5px] text-charcoal-700 leading-relaxed">
          {block.rationale}
        </p>
      )}
      {block.drivers?.length > 0 && (
        <div className="mt-1.5 flex flex-wrap gap-1">
          {block.drivers.map((d, i) => (
            <span
              key={i}
              className="rounded bg-charcoal-100 px-1.5 py-0.5 text-[11px] text-charcoal-600"
            >
              {d}
            </span>
          ))}
        </div>
      )}
      <Sources sources={block.sources} />
    </div>
  );
}

// ── KPI banner ─────────────────────────────────────────────────────────────

export function KpiBanner({
  items,
}: {
  items: { label: string; value: React.ReactNode; tone?: "green" | "amber" | "red" }[];
}) {
  return (
    <div className="grid grid-cols-2 gap-px overflow-hidden rounded-lg border border-charcoal-200 bg-charcoal-200 sm:grid-cols-4">
      {items.map((it, i) => (
        <div key={i} className="bg-white px-4 py-3">
          <div className="miq-eyebrow text-charcoal-500">{it.label}</div>
          <div
            className={`mt-1 text-[15px] font-semibold ${
              it.tone === "green"
                ? "text-status-green"
                : it.tone === "amber"
                  ? "text-status-amber"
                  : it.tone === "red"
                    ? "text-status-red"
                    : "text-charcoal-900"
            }`}
          >
            {it.value || "—"}
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Recommendation banner ──────────────────────────────────────────────────

export function RecommendationBanner({
  eyebrow,
  decision,
  tone,
  body,
  right,
}: {
  eyebrow: string;
  decision: string;
  tone: "green" | "amber" | "red" | "neutral";
  body?: string;
  right?: React.ReactNode;
}) {
  const ring =
    tone === "green"
      ? "from-status-green/[0.08] border-status-green/30"
      : tone === "red"
        ? "from-status-red/[0.08] border-status-red/30"
        : tone === "amber"
          ? "from-status-amber/[0.08] border-status-amber/30"
          : "from-steel-700/[0.06] border-charcoal-200";
  return (
    <div
      className={`rounded-lg border bg-gradient-to-br to-transparent p-5 ${ring}`}
    >
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex-1">
          <div className="miq-eyebrow">{eyebrow}</div>
          <div className="mt-1.5">
            <StatusPill tone={tone}>{decision}</StatusPill>
          </div>
          {body && (
            <p className="mt-3 max-w-3xl text-[15px] leading-relaxed text-charcoal-900">
              {body}
            </p>
          )}
        </div>
        {right}
      </div>
    </div>
  );
}

// ── Decision card (generic boardroom block) ────────────────────────────────

export function DecisionCard({
  title,
  eyebrow,
  children,
}: {
  title: string;
  eyebrow?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-lg border border-charcoal-200 bg-white p-4">
      {eyebrow && <div className="miq-eyebrow text-charcoal-500">{eyebrow}</div>}
      <h3 className="text-[15px] font-semibold text-charcoal-900">{title}</h3>
      <div className="mt-3">{children}</div>
    </div>
  );
}

// ── Risk heat map ──────────────────────────────────────────────────────────

const SEVERITY_STYLE: Record<string, string> = {
  critical: "bg-status-redBg text-status-red border-status-red/40",
  high: "bg-status-redBg/60 text-status-red border-status-red/30",
  medium: "bg-status-amberBg text-status-amber border-status-amber/30",
  low: "bg-status-greenBg text-status-green border-status-green/30",
};

function RiskCell({ risk }: { risk: BriefRisk }) {
  const cls = SEVERITY_STYLE[risk.severity] ?? SEVERITY_STYLE.medium;
  return (
    <div className={`rounded-md border px-3 py-2 ${cls}`}>
      <div className="flex items-start justify-between gap-2">
        <span className="text-[12.5px] font-semibold text-charcoal-900">
          {risk.title}
        </span>
        <span className="shrink-0 text-[10px] font-semibold uppercase tracking-wide">
          {risk.severity}
        </span>
      </div>
      {risk.mitigation && (
        <p className="mt-1 text-[11.5px] text-charcoal-700">
          <span className="font-medium">Mitigation:</span> {risk.mitigation}
        </p>
      )}
      <div className="mt-1">
        <BasisChip basis={risk.basis} />
      </div>
    </div>
  );
}

export function RiskHeatMap({
  groups,
}: {
  groups: { label: string; risks: BriefRisk[] }[];
}) {
  return (
    <div className="grid gap-4 md:grid-cols-3">
      {groups.map((g) => (
        <div key={g.label}>
          <div className="miq-eyebrow mb-2 text-charcoal-500">{g.label}</div>
          <div className="flex flex-col gap-2">
            {g.risks.length === 0 ? (
              <p className="text-[12.5px] italic text-charcoal-400">
                None identified.
              </p>
            ) : (
              g.risks.map((r, i) => <RiskCell key={i} risk={r} />)
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Strength / Weakness matrix ─────────────────────────────────────────────

export function StrengthWeaknessMatrix({
  leftLabel,
  rightLabel,
  left,
  right,
}: {
  leftLabel: string;
  rightLabel: string;
  left?: StrategicPoint[];
  right?: StrategicPoint[];
}) {
  return (
    <div className="grid gap-4 md:grid-cols-2">
      <div>
        <div className="miq-eyebrow mb-2 text-status-green">{leftLabel}</div>
        <PointList points={left} tone="positive" />
      </div>
      <div>
        <div className="miq-eyebrow mb-2 text-status-red">{rightLabel}</div>
        <PointList points={right} tone="negative" />
      </div>
    </div>
  );
}

// ── Action tracker ─────────────────────────────────────────────────────────

const PRIORITY_LABEL: Record<string, string> = {
  immediate: "Immediate",
  near_term: "Near-term",
  pre_rfp: "Pre-RFP",
};

function priorityTone(p?: string): "red" | "amber" | "neutral" {
  if (p === "immediate") return "red";
  if (p === "near_term") return "amber";
  return "neutral";
}

export function ActionTracker({ actions }: { actions?: CaptureAction[] }) {
  if (!actions?.length) {
    return <p className="text-charcoal-500 italic text-[13px]">No actions.</p>;
  }
  return (
    <ol className="flex flex-col gap-2">
      {actions.map((a, i) => (
        <li
          key={i}
          className="flex items-start gap-3 rounded-md border border-charcoal-200 px-3 py-2.5"
        >
          <StatusPill tone={priorityTone(a.priority)}>
            {PRIORITY_LABEL[a.priority] ?? a.priority}
          </StatusPill>
          <div className="flex-1">
            <div className="text-[13.5px] font-medium text-charcoal-900">
              {a.action}
            </div>
            {a.rationale && (
              <p className="mt-0.5 text-[12.5px] text-charcoal-700">
                {a.rationale}
              </p>
            )}
            {a.owner && (
              <div className="mt-0.5 text-[11px] text-charcoal-500">
                Owner: {a.owner}
              </div>
            )}
          </div>
        </li>
      ))}
    </ol>
  );
}

// ── Historical evidence panel (Pursuit Memory) ─────────────────────────────

function HistRow({ label, items }: { label: string; items: string[] }) {
  if (!items?.length) return null;
  return (
    <div>
      <div className="miq-eyebrow mb-1 text-charcoal-500">{label}</div>
      <ul className="flex flex-wrap gap-1.5">
        {items.map((it, i) => (
          <li
            key={i}
            className="rounded border border-navy-700/20 bg-navy-700/[0.06] px-2 py-0.5 text-[12px] text-charcoal-800"
          >
            {it}
          </li>
        ))}
      </ul>
    </div>
  );
}

export function HistoricalEvidencePanel({
  evidence,
}: {
  evidence?: HistoricalEvidence;
}) {
  if (!evidence) return null;
  const empty =
    !evidence.similar_opportunities?.length &&
    !evidence.historical_win_themes?.length &&
    !evidence.historical_risks?.length &&
    !evidence.historical_discriminators?.length &&
    !evidence.agency_patterns?.length;
  if (empty) {
    return (
      <p className="text-[13px] text-charcoal-500">
        No prior pursuit history yet — MissionIQ builds institutional memory as
        you analyze more opportunities.
      </p>
    );
  }
  return (
    <div className="space-y-3">
      <div className="inline-flex items-center rounded bg-navy-700/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-navy-700">
        Historical Evidence — recalled from prior pursuits
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <HistRow label="Similar opportunities" items={evidence.similar_opportunities} />
        <HistRow label="Agency patterns" items={evidence.agency_patterns} />
        <HistRow label="Historical win themes" items={evidence.historical_win_themes} />
        <HistRow label="Historical discriminators" items={evidence.historical_discriminators} />
        <HistRow label="Historical risks" items={evidence.historical_risks} />
      </div>
    </div>
  );
}

// ── Shared helpers exported for pages ──────────────────────────────────────

export function InputsMissingBanner({ missing }: { missing?: string[] }) {
  if (!missing?.length) return null;
  return (
    <div className="rounded-md border border-status-amber/30 bg-status-amberBg px-3 py-2 text-[12.5px] text-charcoal-800">
      <span className="font-semibold">Generated with partial inputs.</span>{" "}
      Missing: {missing.join(", ")}. Generate these upstream modules and
      regenerate for a higher-confidence briefing.
    </div>
  );
}

export function StringList({ items, empty = "—" }: { items?: string[]; empty?: string }) {
  if (!items?.length) {
    return <p className="text-[13px] italic text-charcoal-400">{empty}</p>;
  }
  return (
    <ul className="list-disc space-y-1 pl-4 text-[13px] text-charcoal-800">
      {items.map((it, i) => (
        <li key={i}>{it}</li>
      ))}
    </ul>
  );
}

export { scoreTone };
export type { Confidence };
