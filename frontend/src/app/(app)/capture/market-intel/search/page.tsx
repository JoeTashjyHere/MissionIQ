"use client";

import { useState } from "react";
import { apiRequest, ApiError } from "@/lib/api";
import type { MarketIntelRecord } from "@/lib/types";
import { PageHeader } from "@/components/PageHeader";
import { Card, CardBody, CardHeader } from "@/components/ds/Card";
import { Input } from "@/components/ds/Input";
import { Button } from "@/components/ds/Button";
import { DataTable } from "@/components/ds/DataTable";
import { formatCurrencyCents, formatDate } from "@/lib/format";

interface SearchResponse {
  items: MarketIntelRecord[];
  source: string;
  q: string | null;
  total_estimate: number | null;
}

export default function MarketIntelSearchPage() {
  const [q, setQ] = useState("");
  const [agency, setAgency] = useState("");
  const [naics, setNaics] = useState("");
  const [items, setItems] = useState<MarketIntelRecord[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const search = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({ source: "sam_gov", limit: "25" });
      if (q) params.set("q", q);
      if (agency) params.set("agency", agency);
      if (naics) params.set("naics", naics);
      const resp = await apiRequest<SearchResponse>(`/market-intel/search?${params.toString()}`);
      setItems(resp.items);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Search failed.");
      setItems([]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <PageHeader
        eyebrow="Capture Intelligence · Market Intelligence"
        title="SAM.gov search"
        subtitle="Public opportunity notices from sam.gov. Requires SAM_GOV_API_KEY."
      />

      <Card className="mb-6">
        <CardHeader title="Filters" />
        <CardBody>
          <form
            onSubmit={search}
            className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3 items-end"
          >
            <Input
              label="Keyword"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="e.g. mission operations"
            />
            <Input
              label="Agency"
              value={agency}
              onChange={(e) => setAgency(e.target.value)}
              placeholder="e.g. Defense Health Agency"
            />
            <Input
              label="NAICS"
              value={naics}
              onChange={(e) => setNaics(e.target.value)}
              placeholder="e.g. 541512"
            />
            <Button type="submit" loading={loading}>
              Search
            </Button>
          </form>
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="Results" subtitle="Live results from SAM.gov." />
        <CardBody className="!p-0">
          {error && (
            <div className="p-4 text-status-red text-[13px] bg-status-redBg border-b border-status-red/30">
              {error}
            </div>
          )}
          {items === null ? (
            <div className="p-10 text-center text-charcoal-500 text-[14px]">
              Submit a search to see results.
            </div>
          ) : (
            <DataTable
              columns={[
                {
                  key: "title",
                  header: "Title",
                  render: (r) =>
                    r.source_url ? (
                      <a
                        href={r.source_url}
                        target="_blank"
                        rel="noreferrer"
                        className="font-medium"
                      >
                        {r.title}
                      </a>
                    ) : (
                      <span className="font-medium">{r.title}</span>
                    ),
                },
                { key: "agency", header: "Agency", render: (r) => r.agency || "—" },
                { key: "naics", header: "NAICS", render: (r) => r.naics_code || "—" },
                { key: "type", header: "Type", render: (r) => r.notice_type || "—" },
                { key: "posted", header: "Posted", render: (r) => formatDate(r.posted_date) },
                { key: "due", header: "Due", render: (r) => formatDate(r.due_date) },
                {
                  key: "value",
                  header: "Est. Value",
                  align: "right",
                  render: (r) => (
                    <span className="miq-numeric">{formatCurrencyCents(r.estimated_value_cents)}</span>
                  ),
                },
              ]}
              rows={items}
              emptyState={
                <div className="p-10 text-center text-charcoal-500">No results.</div>
              }
            />
          )}
        </CardBody>
      </Card>
    </div>
  );
}
