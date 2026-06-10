"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { BookOpen, Search, X } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { apiRequest } from "@/lib/api";
import type { ProposalAsset, ProposalAssetDetail } from "@/lib/types";
import { PageHeader } from "@/components/PageHeader";
import { Card, CardBody, CardHeader } from "@/components/ds/Card";
import { DataTable } from "@/components/ds/DataTable";
import { EmptyState } from "@/components/ds/EmptyState";
import { KpiCard } from "@/components/ds/KpiCard";
import { Skeleton } from "@/components/ds/Skeleton";
import { StatusPill } from "@/components/ds/StatusPill";
import { Input } from "@/components/ds/Input";

export type RepositoryLibrary =
  | "all"
  | "past_performance"
  | "win_themes"
  | "staffing"
  | "transition"
  | "executive_summaries";

const LIBRARY_META: Record<
  RepositoryLibrary,
  { title: string; subtitle: string; library: string }
> = {
  all: {
    title: "Proposal Repository",
    subtitle:
      "Reusable institutional proposal intelligence — extracted assets with outcome linkage, not a document library.",
    library: "all",
  },
  past_performance: {
    title: "Past Performance Library",
    subtitle: "Past performance stories with customer, capability, and outcome context.",
    library: "past_performance",
  },
  win_themes: {
    title: "Win Theme Library",
    subtitle: "Win themes and discriminators with historical usage and outcomes.",
    library: "win_themes",
  },
  staffing: {
    title: "Staffing Library",
    subtitle: "Staffing and management narratives reused across pursuits.",
    library: "staffing",
  },
  transition: {
    title: "Transition Library",
    subtitle: "Transition approaches with observed pursuit outcomes.",
    library: "transition",
  },
  executive_summaries: {
    title: "Executive Summary Library",
    subtitle: "Executive summaries by agency with historical outcomes.",
    library: "executive_summaries",
  },
};

function pct(rate: number | null | undefined): string {
  if (rate == null) return "—";
  return `${Math.round(rate * 100)}%`;
}

function outcomeTone(outcome: string | null): "green" | "red" | "neutral" {
  if (outcome === "won") return "green";
  if (outcome === "lost") return "red";
  return "neutral";
}

function AssetDrawer({
  detail,
  onClose,
}: {
  detail: ProposalAssetDetail | null;
  onClose: () => void;
}) {
  if (!detail) return null;
  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-charcoal-900/30">
      <div className="w-full max-w-lg h-full bg-white shadow-xl overflow-y-auto">
        <div className="sticky top-0 flex items-center justify-between border-b border-charcoal-200 bg-white px-5 py-4">
          <div>
            <div className="text-[11px] uppercase tracking-wide text-charcoal-500">
              {detail.asset_type.replaceAll("_", " ")}
            </div>
            <h2 className="text-[16px] font-semibold text-charcoal-900">{detail.title}</h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded p-1 text-charcoal-500 hover:bg-charcoal-100"
            aria-label="Close"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="p-5 flex flex-col gap-5">
          <p className="text-[13.5px] text-charcoal-700">{detail.summary}</p>
          {detail.track_record && (
            <div className="rounded-md border border-steel-200 bg-steel-50 px-3 py-2 text-[12.5px] text-charcoal-800">
              <span className="font-medium">Observed pattern: </span>
              {detail.track_record}
            </div>
          )}
          <div className="grid grid-cols-2 gap-3 text-[12.5px]">
            <div>
              <span className="text-charcoal-500">Agency</span>
              <div className="font-medium">{detail.agency ?? "—"}</div>
            </div>
            <div>
              <span className="text-charcoal-500">Usage</span>
              <div className="font-medium">{detail.usage_count} pursuits</div>
            </div>
            <div>
              <span className="text-charcoal-500">Win rate</span>
              <div className="font-medium miq-numeric">{pct(detail.win_rate)}</div>
            </div>
            <div>
              <span className="text-charcoal-500">Source</span>
              <div className="font-medium truncate">{detail.document_name ?? "—"}</div>
            </div>
          </div>
          {detail.citations.length > 0 && (
            <div>
              <h3 className="text-[12px] font-semibold uppercase tracking-wide text-charcoal-500 mb-2">
                Supporting evidence
              </h3>
              <ul className="flex flex-col gap-2">
                {detail.citations.map((c) => (
                  <li
                    key={c.id}
                    className="rounded border border-charcoal-200 px-3 py-2 text-[12.5px] text-charcoal-700"
                  >
                    {c.page_start != null && (
                      <span className="text-charcoal-500">p.{c.page_start} · </span>
                    )}
                    {c.excerpt}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {detail.usages.length > 0 && (
            <div>
              <h3 className="text-[12px] font-semibold uppercase tracking-wide text-charcoal-500 mb-2">
                Pursuit usage
              </h3>
              <ul className="flex flex-col gap-1.5">
                {detail.usages.map((u) => (
                  <li key={`${u.opportunity_id}-${u.usage_kind}`}>
                    <Link
                      href={`/capture/opportunities/${u.opportunity_id}`}
                      className="text-[13px] text-steel-700 hover:underline"
                    >
                      {u.opportunity_name ?? u.opportunity_id}
                    </Link>
                    {u.outcome && (
                      <StatusPill tone={outcomeTone(u.outcome)} className="ml-2">
                        {u.outcome}
                      </StatusPill>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export function RepositoryWorkbench({ libraryKey }: { libraryKey: RepositoryLibrary }) {
  const { currentWorkspaceId } = useAuth();
  const meta = LIBRARY_META[libraryKey];
  const [assets, setAssets] = useState<ProposalAsset[] | null>(null);
  const [detail, setDetail] = useState<ProposalAssetDetail | null>(null);
  const [q, setQ] = useState("");
  const [agency, setAgency] = useState("");
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!currentWorkspaceId) return;
    setError(null);
    const params = new URLSearchParams({ library: meta.library, limit: "100" });
    if (q.trim()) params.set("q", q.trim());
    if (agency.trim()) params.set("agency", agency.trim());
    const rows = await apiRequest<ProposalAsset[]>(
      `/workspaces/${currentWorkspaceId}/proposal-assets?${params}`,
    );
    setAssets(rows);
  }, [currentWorkspaceId, meta.library, q, agency]);

  useEffect(() => {
    load().catch((e: Error) => setError(e.message));
  }, [load]);

  const openDetail = async (asset: ProposalAsset) => {
    if (!currentWorkspaceId) return;
    const d = await apiRequest<ProposalAssetDetail>(
      `/workspaces/${currentWorkspaceId}/proposal-assets/${asset.id}`,
    );
    setDetail(d);
  };

  const withSignal = assets?.filter((a) => a.wins + a.losses > 0).length ?? 0;

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title={meta.title} subtitle={meta.subtitle} />
      {error && (
        <div className="rounded-md border border-status-red/30 bg-status-redBg px-4 py-3 text-[13px] text-status-red">
          {error}
        </div>
      )}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <KpiCard label="Intelligence assets" value={assets?.length ?? "—"} />
        <KpiCard label="With outcome signal" value={assets ? withSignal : "—"} />
        <KpiCard
          label="Avg win rate"
          value={
            assets && assets.length
              ? pct(
                  assets.filter((a) => a.win_rate != null).length
                    ? assets
                        .filter((a) => a.win_rate != null)
                        .reduce((s, a) => s + (a.win_rate ?? 0), 0) /
                      assets.filter((a) => a.win_rate != null).length
                    : null,
                )
              : "—"
          }
        />
      </div>
      <Card>
        <CardHeader title="Search & filter" />
        <CardBody>
          <div className="flex flex-wrap gap-3 items-end">
            <div className="flex-1 min-w-[200px]">
              <label className="text-[12px] text-charcoal-600 mb-1 block">Search</label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-charcoal-400" />
                <Input
                  value={q}
                  onChange={(e) => setQ(e.target.value)}
                  placeholder="Title, summary, tags…"
                  className="pl-9"
                />
              </div>
            </div>
            <div className="w-48">
              <label className="text-[12px] text-charcoal-600 mb-1 block">Agency</label>
              <Input
                value={agency}
                onChange={(e) => setAgency(e.target.value)}
                placeholder="e.g. CMS"
              />
            </div>
            <button
              type="button"
              onClick={() => load().catch((e: Error) => setError(e.message))}
              className="miq-btn-primary px-4 py-2 text-[13px]"
            >
              Apply
            </button>
          </div>
        </CardBody>
      </Card>
      <Card>
        <CardHeader title="Intelligence assets" />
        <CardBody className="!p-0">
          {assets === null ? (
            <div className="p-6 flex flex-col gap-2">
              {[0, 1, 2].map((i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : assets.length === 0 ? (
            <EmptyState
              icon={<BookOpen />}
              title="No proposal intelligence yet"
              description="Upload proposal documents (type: proposal or proposal volume) and run extraction to populate this repository."
            />
          ) : (
            <DataTable
              columns={[
                {
                  key: "title",
                  header: "Asset",
                  render: (a) => (
                    <button
                      type="button"
                      onClick={() => openDetail(a).catch((e: Error) => setError(e.message))}
                      className="text-left hover:underline text-charcoal-900 font-medium"
                    >
                      {a.title}
                    </button>
                  ),
                },
                {
                  key: "type",
                  header: "Type",
                  render: (a) => (
                    <span className="text-[12px] text-charcoal-600">
                      {a.asset_type.replaceAll("_", " ")}
                    </span>
                  ),
                },
                { key: "agency", header: "Agency", render: (a) => a.agency ?? "—" },
                {
                  key: "outcome",
                  header: "Outcome",
                  render: (a) =>
                    a.outcome ? (
                      <StatusPill tone={outcomeTone(a.outcome)}>{a.outcome}</StatusPill>
                    ) : (
                      "—"
                    ),
                },
                {
                  key: "usage",
                  header: "Usage",
                  align: "right",
                  render: (a) => a.usage_count,
                },
                {
                  key: "win_rate",
                  header: "Win rate",
                  align: "right",
                  render: (a) => (
                    <span className="miq-numeric">{pct(a.win_rate)}</span>
                  ),
                },
                {
                  key: "track",
                  header: "Observed pattern",
                  render: (a) => (
                    <span className="text-[12px] text-charcoal-600">
                      {a.track_record ?? "—"}
                    </span>
                  ),
                },
              ]}
              rows={assets}
            />
          )}
        </CardBody>
      </Card>
      <AssetDrawer detail={detail} onClose={() => setDetail(null)} />
    </div>
  );
}
