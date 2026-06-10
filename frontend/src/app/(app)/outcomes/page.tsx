"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Scale, Target, TrendingUp } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { ApiError, apiRequest } from "@/lib/api";
import type {
  OutcomeIntelligenceReport,
  OutcomePattern,
  PursuitOutcome,
} from "@/lib/types";
import { formatCurrencyCents, formatDate } from "@/lib/format";
import { OUTCOME_LABEL, outcomeTone } from "@/lib/outcomes";
import { PageHeader } from "@/components/PageHeader";
import { Card, CardBody, CardHeader } from "@/components/ds/Card";
import { DataTable } from "@/components/ds/DataTable";
import { EmptyState } from "@/components/ds/EmptyState";
import { KpiCard } from "@/components/ds/KpiCard";
import { StatusPill } from "@/components/ds/StatusPill";

function pct(rate: number | null | undefined): string {
  if (rate == null) return "—";
  return `${Math.round(rate * 100)}%`;
}

/** Small W/L record bar — wins (green) vs losses (red). */
function RecordBar({ wins, losses }: { wins: number; losses: number }) {
  const total = wins + losses;
  if (total === 0) return <span className="text-charcoal-500">—</span>;
  return (
    <div className="flex items-center gap-2">
      <div className="flex h-2 w-24 overflow-hidden rounded-full bg-charcoal-100">
        <div
          className="bg-status-green"
          style={{ width: `${(wins / total) * 100}%` }}
        />
        <div
          className="bg-status-red"
          style={{ width: `${(losses / total) * 100}%` }}
        />
      </div>
      <span className="miq-numeric text-[12px] text-charcoal-700 whitespace-nowrap">
        {wins}W–{losses}L
      </span>
    </div>
  );
}

function SourceChips({ pattern }: { pattern: OutcomePattern }) {
  return (
    <div className="mt-1.5 flex flex-wrap gap-1">
      {pattern.source_pursuits.map((s) => (
        <Link
          key={`${s.id}-${s.outcome}`}
          href={`/capture/opportunities/${s.id}`}
          className={`rounded px-1.5 py-0.5 text-[10.5px] font-medium hover:underline ${
            s.outcome === "won"
              ? "bg-status-greenBg text-status-green"
              : "bg-status-redBg text-status-red"
          }`}
        >
          {s.name}
        </Link>
      ))}
    </div>
  );
}

function PatternList({
  patterns,
  empty,
}: {
  patterns: OutcomePattern[];
  empty: string;
}) {
  if (!patterns.length) {
    return <p className="text-[13px] italic text-charcoal-500">{empty}</p>;
  }
  return (
    <ul className="flex flex-col gap-2.5">
      {patterns.map((p, i) => (
        <li
          key={`${p.entity_type}-${p.label}-${i}`}
          className="rounded-md border border-charcoal-200 px-3 py-2.5"
        >
          <div className="flex items-start justify-between gap-3">
            <div>
              <span className="text-[13.5px] font-medium text-charcoal-900">
                {p.label}
              </span>
              <span className="ml-2 text-[11px] uppercase tracking-wide text-charcoal-500">
                {p.entity_type.replaceAll("_", " ")}
              </span>
            </div>
            <RecordBar wins={p.wins} losses={p.losses} />
          </div>
          <p className="mt-1 text-[12.5px] text-charcoal-700">{p.observation}</p>
          <SourceChips pattern={p} />
        </li>
      ))}
    </ul>
  );
}

const REC_TYPE_LABEL: Record<string, string> = {
  bid_decision: "Bid / No-Bid Decision",
  gate_recommendation: "Gate Review Recommendation",
  win_confidence: "Win Confidence (Win Strategy)",
  executive_recommendation: "Executive Brief Recommendation",
};

export default function OutcomeIntelligencePage() {
  const { currentWorkspaceId } = useAuth();
  const [report, setReport] = useState<OutcomeIntelligenceReport | null>(null);
  const [outcomes, setOutcomes] = useState<PursuitOutcome[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!currentWorkspaceId) return;
    Promise.all([
      apiRequest<OutcomeIntelligenceReport>(
        `/workspaces/${currentWorkspaceId}/outcome-intelligence`,
      ),
      apiRequest<PursuitOutcome[]>(`/workspaces/${currentWorkspaceId}/outcomes`),
    ])
      .then(([r, o]) => {
        setReport(r);
        setOutcomes(o);
      })
      .catch((e) =>
        setError(
          e instanceof ApiError ? e.detail : "Failed to load outcome intelligence.",
        ),
      );
  }, [currentWorkspaceId]);

  const s = report?.summary;
  const noHistory = report !== null && s !== undefined && s.recorded === 0;

  return (
    <div>
      <PageHeader
        eyebrow="MissionIQ · Memory · Improve"
        title="Outcome Intelligence"
        subtitle={
          "The closed learning loop: recorded pursuit outcomes, win/loss " +
          "patterns, agency and competitor trends, and how MissionIQ's " +
          "recommendations aligned with what actually happened. Everything " +
          "here is an observed pattern or historical correlation with " +
          "supporting evidence — never a causal claim."
        }
      />

      {error && (
        <div className="mb-4 rounded-md p-4 text-status-red text-[13px] bg-status-redBg border border-status-red/30">
          {error}
        </div>
      )}

      {noHistory ? (
        <Card>
          <CardBody>
            <EmptyState
              icon={<TrendingUp />}
              title="No pursuit outcomes recorded yet"
              description={
                "MissionIQ becomes smarter with every completed pursuit. Record " +
                "the outcome (won, lost, no-bid) from a pursuit's briefing page " +
                "to activate win/loss patterns, trends, and recommendation " +
                "performance tracking."
              }
              action={
                <Link
                  href="/capture/opportunities"
                  className="text-steel-700 text-[13px] font-medium hover:underline"
                >
                  Go to Opportunities →
                </Link>
              }
            />
          </CardBody>
        </Card>
      ) : (
        <>
          {/* ── KPI banner ─────────────────────────────────────────────── */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            <KpiCard
              label="Decided Pursuits"
              value={s ? s.decided : "—"}
              helper={s ? `${s.recorded} outcome(s) recorded` : undefined}
            />
            <KpiCard
              label="Historical Win Rate"
              value={s ? pct(s.win_rate) : "—"}
              tone={
                s?.win_rate == null
                  ? undefined
                  : s.win_rate >= 0.5
                    ? "green"
                    : "red"
              }
              helper={s ? `${s.wins} won · ${s.losses} lost` : undefined}
            />
            <KpiCard
              label="Value Won"
              value={s ? formatCurrencyCents(s.value_won_cents) : "—"}
              helper="Recorded award value"
            />
            <KpiCard
              label="Recommendation Alignment"
              value={s ? pct(s.recommendation_alignment_rate) : "—"}
              helper="Historical correlation — not causal accuracy"
            />
          </div>

          {/* ── Win / Loss analysis ────────────────────────────────────── */}
          <div id="winloss" className="scroll-mt-6 grid gap-6 lg:grid-cols-2 mb-6">
            <Card>
              <CardHeader
                title="Win patterns"
                eyebrow="Observed patterns"
                subtitle="Items that appeared most in won pursuits, weighted by smoothed historical win rate."
              />
              <CardBody>
                <PatternList
                  patterns={report?.win_patterns ?? []}
                  empty="No win patterns observed yet — record your first won pursuit."
                />
              </CardBody>
            </Card>
            <Card>
              <CardHeader
                title="Loss patterns"
                eyebrow="Historical correlations"
                subtitle="Items that recurred in lost pursuits — recurring risks and themes to pre-empt."
              />
              <CardBody>
                <PatternList
                  patterns={report?.loss_patterns ?? []}
                  empty="No loss patterns observed yet."
                />
              </CardBody>
            </Card>
          </div>

          {report !== null && report.factor_frequencies.length > 0 && (
            <Card className="mb-6">
              <CardHeader
                title="Debrief factors"
                eyebrow="As recorded in outcome debriefs"
                subtitle="How often each factor was cited in wins vs. losses."
              />
              <CardBody className="!p-0">
                <DataTable
                  columns={[
                    { key: "factor", header: "Factor", render: (f) => f.factor },
                    {
                      key: "wins",
                      header: "Cited in Wins",
                      render: (f) => (
                        <span className="miq-numeric">{f.in_wins}</span>
                      ),
                    },
                    {
                      key: "losses",
                      header: "Cited in Losses",
                      render: (f) => (
                        <span
                          className={
                            f.in_losses > f.in_wins
                              ? "miq-numeric text-status-red font-medium"
                              : "miq-numeric"
                          }
                        >
                          {f.in_losses}
                        </span>
                      ),
                    },
                  ]}
                  rows={report.factor_frequencies}
                  emptyState={<div className="p-6 text-charcoal-500">—</div>}
                />
              </CardBody>
            </Card>
          )}

          {/* ── Trends ─────────────────────────────────────────────────── */}
          <div id="trends" className="scroll-mt-6 flex flex-col gap-6 mb-6">
            <Card>
              <CardHeader
                title="Agency trends"
                eyebrow="Where we win and lose"
                subtitle="Decided-pursuit record per agency, with recorded award value."
              />
              <CardBody className="!p-0">
                {report !== null && report.agency_trends.length === 0 ? (
                  <div className="p-6 text-[13px] italic text-charcoal-500">
                    No agency outcome history yet.
                  </div>
                ) : (
                  <DataTable
                    columns={[
                      { key: "agency", header: "Agency", render: (a) => a.label },
                      {
                        key: "record",
                        header: "Record",
                        render: (a) => <RecordBar wins={a.wins} losses={a.losses} />,
                      },
                      {
                        key: "rate",
                        header: "Win Rate",
                        render: (a) => (
                          <span className="miq-numeric">{pct(a.win_rate)}</span>
                        ),
                      },
                      {
                        key: "value",
                        header: "Value Won",
                        render: (a) => (
                          <span className="miq-numeric">
                            {formatCurrencyCents(a.decided_value_cents ?? 0)}
                          </span>
                        ),
                      },
                    ]}
                    rows={report?.agency_trends ?? []}
                    emptyState={<div className="p-6 text-charcoal-500">Loading…</div>}
                  />
                )}
              </CardBody>
            </Card>

            <div className="grid gap-6 lg:grid-cols-2">
              <Card>
                <CardHeader
                  title="Capability trends"
                  eyebrow="Capabilities across decided pursuits"
                />
                <CardBody>
                  <PatternList
                    patterns={report?.capability_trends ?? []}
                    empty="No capability outcome history yet."
                  />
                </CardBody>
              </Card>
              <Card>
                <CardHeader
                  title="Competitor trends"
                  eyebrow="Our record where each competitor appeared"
                  subtitle="“Awards taken” counts recorded losses where the competitor won."
                />
                <CardBody className="!p-0">
                  {report !== null && report.competitor_trends.length === 0 ? (
                    <div className="p-6 text-[13px] italic text-charcoal-500">
                      No competitor outcome history yet.
                    </div>
                  ) : (
                    <DataTable
                      columns={[
                        {
                          key: "competitor",
                          header: "Competitor",
                          render: (c) => c.label,
                        },
                        {
                          key: "record",
                          header: "Our Record",
                          render: (c) => (
                            <RecordBar wins={c.wins} losses={c.losses} />
                          ),
                        },
                        {
                          key: "taken",
                          header: "Awards Taken",
                          render: (c) => (
                            <span
                              className={
                                (c.awards_taken ?? 0) > 0
                                  ? "miq-numeric text-status-red font-medium"
                                  : "miq-numeric text-charcoal-500"
                              }
                            >
                              {c.awards_taken ?? 0}
                            </span>
                          ),
                        },
                      ]}
                      rows={report?.competitor_trends ?? []}
                      emptyState={
                        <div className="p-6 text-charcoal-500">Loading…</div>
                      }
                    />
                  )}
                </CardBody>
              </Card>
            </div>
          </div>

          {/* ── Recommendation performance ─────────────────────────────── */}
          <div id="recommendations" className="scroll-mt-6 flex flex-col gap-6 mb-6">
            <Card>
              <CardHeader
                title="Recommendation performance"
                eyebrow="How MissionIQ's recommendations aligned with recorded outcomes"
                subtitle="Alignment is a historical correlation between a recommendation and the recorded outcome — not a causal accuracy measure."
              />
              <CardBody className="!p-0">
                {report !== null &&
                report.recommendation_performance.length === 0 ? (
                  <div className="p-6">
                    <EmptyState
                      icon={<Scale />}
                      title="No assessed recommendations yet"
                      description="When an outcome is recorded, MissionIQ snapshots the recommendations it made for that pursuit and tracks alignment here."
                    />
                  </div>
                ) : (
                  <DataTable
                    columns={[
                      {
                        key: "type",
                        header: "Recommendation",
                        render: (p) => (
                          <div>
                            <div className="font-medium">
                              {REC_TYPE_LABEL[p.recommendation_type] ??
                                p.recommendation_type}
                            </div>
                            <div className="text-[12px] text-charcoal-500">
                              {p.module_id}
                            </div>
                          </div>
                        ),
                      },
                      {
                        key: "assessed",
                        header: "Assessed",
                        render: (p) => <span className="miq-numeric">{p.total}</span>,
                      },
                      {
                        key: "aligned",
                        header: "Aligned",
                        render: (p) => (
                          <span className="miq-numeric">{p.aligned}</span>
                        ),
                      },
                      {
                        key: "rate",
                        header: "Alignment Rate",
                        render: (p) => (
                          <span className="miq-numeric">
                            {pct(p.alignment_rate)}
                          </span>
                        ),
                      },
                    ]}
                    rows={report?.recommendation_performance ?? []}
                    emptyState={<div className="p-6 text-charcoal-500">Loading…</div>}
                  />
                )}
              </CardBody>
            </Card>

            {report !== null &&
              report.calibration.some((b) => b.predictions > 0) && (
                <Card>
                  <CardHeader
                    title="Win-confidence calibration"
                    eyebrow="Predicted win confidence vs. observed outcomes"
                    subtitle="Historical correlation across decided pursuits — small samples; read directionally."
                  />
                  <CardBody>
                    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                      {report.calibration.map((b) => (
                        <div
                          key={b.range_label}
                          className="rounded-md border border-charcoal-200 px-3 py-2.5"
                        >
                          <div className="miq-eyebrow text-charcoal-500">
                            Predicted {b.range_label}
                          </div>
                          <div className="mt-1 miq-numeric text-[20px] font-semibold text-charcoal-900">
                            {pct(b.observed_win_rate)}
                          </div>
                          <div className="text-[11.5px] text-charcoal-500">
                            observed · {b.predictions} prediction(s)
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardBody>
                </Card>
              )}
          </div>

          {/* ── Strategic observations ─────────────────────────────────── */}
          {report !== null && report.strategic_observations.length > 0 && (
            <Card className="mb-6">
              <CardHeader
                title="Strategic observations"
                eyebrow="Deterministic, evidence-cited"
                subtitle="For pursuit-specific synthesis, run the Outcome Intelligence module on an opportunity (Outcome Intel tab)."
              />
              <CardBody>
                <ul className="flex flex-col gap-2.5">
                  {report.strategic_observations.map((o, i) => (
                    <li
                      key={i}
                      className="rounded-md border border-charcoal-200 px-3 py-2.5"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <p className="text-[13.5px] text-charcoal-900 leading-relaxed">
                          {o.observation}
                        </p>
                        <StatusPill
                          tone={o.kind === "observed_pattern" ? "info" : "neutral"}
                          className="shrink-0"
                        >
                          {o.kind === "observed_pattern"
                            ? "Observed Pattern"
                            : "Historical Correlation"}
                        </StatusPill>
                      </div>
                      {o.sources.length > 0 && (
                        <div className="mt-1 flex flex-wrap gap-1">
                          {o.sources.map((src, j) => (
                            <span
                              key={j}
                              className="rounded bg-charcoal-100 px-1.5 py-0.5 text-[10px] font-mono text-charcoal-600"
                            >
                              {src}
                            </span>
                          ))}
                        </div>
                      )}
                    </li>
                  ))}
                </ul>
              </CardBody>
            </Card>
          )}

          {/* ── Recorded outcomes ──────────────────────────────────────── */}
          <Card>
            <CardHeader
              title="Recorded outcomes"
              eyebrow="The institutional record"
              subtitle="Every recorded pursuit outcome feeding the analysis above."
            />
            <CardBody className="!p-0">
              {outcomes !== null && outcomes.length === 0 ? (
                <div className="p-6">
                  <EmptyState
                    icon={<Target />}
                    title="No outcomes recorded"
                    description="Record outcomes from each pursuit's briefing page."
                  />
                </div>
              ) : (
                <DataTable
                  columns={[
                    {
                      key: "pursuit",
                      header: "Pursuit",
                      render: (o: PursuitOutcome) => (
                        <Link
                          href={`/capture/opportunities/${o.opportunity_id}`}
                          className="font-medium text-steel-700 hover:underline"
                        >
                          {o.opportunity_name ?? "View pursuit"}
                        </Link>
                      ),
                    },
                    {
                      key: "outcome",
                      header: "Outcome",
                      render: (o) => (
                        <StatusPill tone={outcomeTone(o.outcome)}>
                          {OUTCOME_LABEL[o.outcome] ?? o.outcome}
                        </StatusPill>
                      ),
                    },
                    {
                      key: "agency",
                      header: "Agency",
                      render: (o) => (
                        <span className="text-[13px]">{o.agency ?? "—"}</span>
                      ),
                    },
                    {
                      key: "decided",
                      header: "Decided",
                      render: (o) => (
                        <span className="text-[13px]">
                          {formatDate(o.decided_at)}
                        </span>
                      ),
                    },
                    {
                      key: "value",
                      header: "Award Value",
                      render: (o) => (
                        <span className="miq-numeric">
                          {formatCurrencyCents(o.awarded_value_cents)}
                        </span>
                      ),
                    },
                    {
                      key: "winner",
                      header: "Awarded To",
                      render: (o) => (
                        <span className="text-[13px]">
                          {o.outcome === "won"
                            ? "Us"
                            : (o.awarded_to_competitor ?? "—")}
                        </span>
                      ),
                    },
                  ]}
                  rows={outcomes ?? []}
                  emptyState={<div className="p-6 text-charcoal-500">Loading…</div>}
                />
              )}
            </CardBody>
          </Card>
        </>
      )}
    </div>
  );
}
