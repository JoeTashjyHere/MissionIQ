"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { apiRequest } from "@/lib/api";
import type {
  AgencyIntelligence,
  MemoryBasis,
  MemoryItem,
  PursuitMemory,
  SimilarOpportunity,
} from "@/lib/types";
import { PageHeader } from "@/components/PageHeader";
import { Card, CardBody, CardHeader } from "@/components/ds/Card";
import { Skeleton } from "@/components/ds/Skeleton";
import { Brain, History, Network } from "lucide-react";

const BASIS_STYLE: Record<MemoryBasis, { label: string; cls: string }> = {
  historical: {
    label: "Historical Evidence",
    cls: "bg-steel-700/10 text-steel-700",
  },
  current: {
    label: "Current Opportunity",
    cls: "bg-status-greenBg text-status-green",
  },
  inference: {
    label: "Inference",
    cls: "bg-status-amberBg text-status-amber",
  },
};

function BasisChip({ basis }: { basis: MemoryBasis }) {
  const s = BASIS_STYLE[basis];
  return (
    <span
      className={`inline-flex items-center rounded px-1.5 py-0.5 text-[10.5px] font-semibold uppercase tracking-wide ${s.cls}`}
    >
      {s.label}
    </span>
  );
}

function BasisLegend() {
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-[12px] text-charcoal-500">
      <span className="font-medium text-charcoal-700">How to read this:</span>
      {(Object.keys(BASIS_STYLE) as MemoryBasis[]).map((b) => (
        <span key={b} className="inline-flex items-center gap-1.5">
          <BasisChip basis={b} />
          <span>
            {b === "historical"
              ? "recalled from prior pursuits"
              : b === "current"
                ? "seen on this opportunity"
                : "MissionIQ's aggregated judgment"}
          </span>
        </span>
      ))}
    </div>
  );
}

function ItemRow({ item }: { item: MemoryItem }) {
  return (
    <div className="border-b border-charcoal-100 py-3 last:border-0">
      <div className="flex items-start justify-between gap-3">
        <p className="text-[13.5px] text-charcoal-900">{item.label}</p>
        <BasisChip basis={item.basis} />
      </div>
      <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11.5px] text-charcoal-500">
        {item.frequency > 0 && (
          <span>
            seen on {item.frequency} prior pursuit
            {item.frequency === 1 ? "" : "s"}
          </span>
        )}
        {item.source_opportunities.length > 0 && (
          <span className="flex flex-wrap gap-1.5">
            {item.source_opportunities.slice(0, 4).map((s) => (
              <Link
                key={s.id}
                href={`/capture/opportunities/${s.id}`}
                className="rounded bg-charcoal-100 px-1.5 py-0.5 text-charcoal-600 hover:text-steel-700"
              >
                {s.name}
              </Link>
            ))}
          </span>
        )}
      </div>
    </div>
  );
}

function ItemListCard({
  title,
  eyebrow,
  items,
  empty,
}: {
  title: string;
  eyebrow: string;
  items: MemoryItem[];
  empty: string;
}) {
  return (
    <Card>
      <CardHeader eyebrow={eyebrow} title={title} />
      <CardBody className="py-2">
        {items.length === 0 ? (
          <p className="py-3 text-[13px] text-charcoal-400">{empty}</p>
        ) : (
          items.map((item, i) => <ItemRow key={i} item={item} />)
        )}
      </CardBody>
    </Card>
  );
}

function SimilarCard({
  similar,
}: {
  similar: SimilarOpportunity[];
}) {
  return (
    <Card>
      <CardHeader
        eyebrow="Opportunity Similarity Engine"
        title="Similar Prior Pursuits"
        subtitle="Ranked by agency, vehicle, NAICS, and shared signals"
      />
      <CardBody className="py-2">
        {similar.length === 0 ? (
          <p className="py-3 text-[13px] text-charcoal-400">
            No similar prior opportunities yet.
          </p>
        ) : (
          similar.map((s) => (
            <div
              key={s.opportunity_id}
              className="border-b border-charcoal-100 py-3 last:border-0"
            >
              <div className="flex items-start justify-between gap-3">
                <Link
                  href={`/capture/opportunities/${s.opportunity_id}`}
                  className="text-[13.5px] font-medium text-charcoal-900 hover:text-steel-700"
                >
                  {s.name}
                </Link>
                <span className="shrink-0 rounded bg-steel-700/10 px-2 py-0.5 text-[11px] font-semibold text-steel-700">
                  {Math.round(s.score * 100)}% match
                </span>
              </div>
              {s.agency && (
                <p className="mt-0.5 text-[12px] text-charcoal-500">{s.agency}</p>
              )}
              {s.reasons.length > 0 && (
                <ul className="mt-1.5 flex flex-wrap gap-1.5">
                  {s.reasons.map((r, i) => (
                    <li
                      key={i}
                      className="rounded bg-charcoal-100 px-1.5 py-0.5 text-[11px] text-charcoal-600"
                    >
                      {r}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          ))
        )}
      </CardBody>
    </Card>
  );
}

function AgencyCard({ intel }: { intel: AgencyIntelligence }) {
  return (
    <Card>
      <CardHeader
        eyebrow="Agency Intelligence Repository"
        title={intel.agency || "Agency"}
        subtitle={`${intel.opportunities_count} pursuit${
          intel.opportunities_count === 1 ? "" : "s"
        } on record for this agency`}
      />
      <CardBody className="space-y-4">
        {intel.mission && (
          <div>
            <div className="miq-eyebrow mb-1">Mission</div>
            <p className="text-[13px] text-charcoal-700">{intel.mission}</p>
          </div>
        )}
        {intel.strategic_goals.length > 0 && (
          <div>
            <div className="miq-eyebrow mb-1">Strategic Goals</div>
            <ul className="list-disc pl-4 text-[13px] text-charcoal-700">
              {intel.strategic_goals.map((g, i) => (
                <li key={i}>{g}</li>
              ))}
            </ul>
          </div>
        )}
        <div className="grid gap-4 sm:grid-cols-3">
          <AgencyMini title="Recurring Risks" items={intel.recurring_risks} />
          <AgencyMini title="Win Themes" items={intel.recurring_win_themes} />
          <AgencyMini title="Known Competitors" items={intel.known_competitors} />
        </div>
      </CardBody>
    </Card>
  );
}

function AgencyMini({ title, items }: { title: string; items: MemoryItem[] }) {
  return (
    <div>
      <div className="miq-eyebrow mb-1.5">{title}</div>
      {items.length === 0 ? (
        <p className="text-[12px] text-charcoal-400">None recorded.</p>
      ) : (
        <ul className="space-y-1">
          {items.map((it, i) => (
            <li key={i} className="text-[12.5px] text-charcoal-700">
              {it.label}
              {it.frequency > 1 && (
                <span className="text-charcoal-400"> ×{it.frequency}</span>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function MemoryPage({
  params,
}: {
  params: Promise<{ opportunityId: string }>;
}) {
  const { opportunityId } = use(params);
  const [memory, setMemory] = useState<PursuitMemory | null | undefined>(
    undefined,
  );

  useEffect(() => {
    apiRequest<PursuitMemory>(`/opportunities/${opportunityId}/memory`)
      .then(setMemory)
      .catch(() => setMemory(null));
  }, [opportunityId]);

  if (memory === undefined) {
    return (
      <div className="flex flex-col gap-4">
        <Skeleton className="h-10 w-1/2" />
        <Skeleton className="h-24" />
        <Skeleton className="h-64" />
      </div>
    );
  }

  if (memory === null) {
    return (
      <div>
        <PageHeader
          title="Pursuit Memory"
          subtitle="MissionIQ's institutional intelligence for this pursuit"
        />
        <Card>
          <CardBody>
            <p className="text-[13px] text-charcoal-500">
              Could not load pursuit memory. Try again shortly.
            </p>
          </CardBody>
        </Card>
      </div>
    );
  }

  const statEntries = Object.entries(memory.graph_stats || {}).filter(
    ([, n]) => n > 0,
  );

  return (
    <div className="space-y-6">
      <PageHeader
        title="Pursuit Memory"
        subtitle="MissionIQ recalls what it learned on prior pursuits — and gets smarter with every opportunity"
      />

      <Card variant="outline">
        <CardBody className="space-y-3">
          <div className="flex items-start gap-3">
            <Brain className="mt-0.5 h-5 w-5 shrink-0 text-steel-700" />
            <p className="text-[14px] text-charcoal-800">{memory.summary}</p>
          </div>
          <BasisLegend />
        </CardBody>
      </Card>

      {!memory.has_history && (
        <Card>
          <CardBody>
            <div className="flex items-start gap-3">
              <History className="mt-0.5 h-5 w-5 shrink-0 text-charcoal-400" />
              <p className="text-[13.5px] text-charcoal-600">
                This is net-new institutional ground. As you analyze more
                opportunities, MissionIQ links them into a knowledge graph and
                this page fills with similar pursuits, recurring risks, reusable
                discriminators, and proven win themes — automatically.
              </p>
            </div>
          </CardBody>
        </Card>
      )}

      <SimilarCard similar={memory.similar_opportunities} />

      <div className="grid gap-6 lg:grid-cols-3">
        <ItemListCard
          eyebrow="Pursuit Memory"
          title="Prior Risks"
          items={memory.prior_risks}
          empty="No prior risks recalled."
        />
        <ItemListCard
          eyebrow="Pursuit Memory"
          title="Prior Discriminators"
          items={memory.prior_discriminators}
          empty="No prior discriminators recalled."
        />
        <ItemListCard
          eyebrow="Pursuit Memory"
          title="Prior Win Themes"
          items={memory.prior_win_themes}
          empty="No prior win themes recalled."
        />
      </div>

      {memory.inferences.length > 0 && (
        <Card>
          <CardHeader
            eyebrow="Synthesized"
            title="What MissionIQ Infers"
          />
          <CardBody className="space-y-2">
            {memory.inferences.map((inf, i) => (
              <div key={i} className="flex items-start gap-2">
                <BasisChip basis="inference" />
                <p className="text-[13.5px] text-charcoal-800">{inf}</p>
              </div>
            ))}
          </CardBody>
        </Card>
      )}

      {memory.agency_intelligence && (
        <AgencyCard intel={memory.agency_intelligence} />
      )}

      {statEntries.length > 0 && (
        <Card variant="subtle">
          <CardBody>
            <div className="flex items-center gap-2 mb-3">
              <Network className="h-4 w-4 text-charcoal-400" />
              <span className="miq-eyebrow">Knowledge Graph</span>
            </div>
            <div className="flex flex-wrap gap-x-6 gap-y-2">
              {statEntries.map(([type, n]) => (
                <div key={type} className="text-[13px]">
                  <span className="font-semibold text-charcoal-900">{n}</span>{" "}
                  <span className="text-charcoal-500">
                    {type.replace(/_/g, " ")}
                  </span>
                </div>
              ))}
            </div>
          </CardBody>
        </Card>
      )}
    </div>
  );
}
