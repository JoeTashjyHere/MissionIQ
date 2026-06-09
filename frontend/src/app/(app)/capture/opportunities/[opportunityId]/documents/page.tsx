"use client";

import { use, useEffect, useRef, useState } from "react";
import { apiRequest, getAccessToken } from "@/lib/api";
import type { DocumentRecord } from "@/lib/types";
import { PageHeader } from "@/components/PageHeader";
import { Card, CardBody, CardHeader } from "@/components/ds/Card";
import { DataTable } from "@/components/ds/DataTable";
import { StatusPill } from "@/components/ds/StatusPill";
import { Select } from "@/components/ds/Select";
import { Skeleton } from "@/components/ds/Skeleton";
import { formatDateTime } from "@/lib/format";

const DOC_TYPES = [
  "rfp",
  "rfi",
  "sources_sought",
  "pws",
  "sow",
  "soo",
  "qasp",
  "sections_l_m",
  "evaluation_criteria",
  "past_performance",
  "capture_notes",
  "internal_solution",
  "other",
];

function statusTone(s: string): "green" | "amber" | "red" | "neutral" {
  if (s === "ready") return "green";
  if (s === "failed") return "red";
  if (s === "uploaded" || s === "extracting" || s === "chunking" || s === "embedding") {
    return "amber";
  }
  return "neutral";
}

export default function DocumentsPage({
  params,
}: {
  params: Promise<{ opportunityId: string }>;
}) {
  const { opportunityId } = use(params);
  const [docs, setDocs] = useState<DocumentRecord[] | null>(null);
  const [docType, setDocType] = useState("rfp");
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const refresh = async () => {
    const r = await apiRequest<DocumentRecord[]>(
      `/opportunities/${opportunityId}/documents`,
    );
    setDocs(r);
  };

  useEffect(() => {
    refresh().catch(() => setDocs([]));
    const t = setInterval(() => {
      refresh().catch(() => undefined);
    }, 4000);
    return () => clearInterval(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [opportunityId]);

  const onUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("doc_type", docType);
      const token = getAccessToken();
      const resp = await fetch(
        `${process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1"}/opportunities/${opportunityId}/documents`,
        {
          method: "POST",
          headers: token ? { Authorization: `Bearer ${token}` } : undefined,
          body: fd,
        },
      );
      if (!resp.ok) {
        const text = await resp.text();
        throw new Error(text);
      }
      await refresh();
    } catch (err) {
      console.error(err);
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  return (
    <div>
      <PageHeader
        eyebrow="Capture Intelligence · Documents"
        title="Opportunity documents"
        subtitle="Upload RFPs, PWS/SOW/SOO, evaluation criteria, capture notes, and supporting docs."
      />

      <Card className="mb-6">
        <CardHeader title="Upload" subtitle="PDF, DOCX, or TXT up to 50 MB." />
        <CardBody>
          <div className="flex flex-wrap items-end gap-3">
            <div className="w-[220px]">
              <Select
                label="Document type"
                value={docType}
                onChange={(e) => setDocType(e.target.value)}
              >
                {DOC_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </Select>
            </div>
            <input
              ref={fileRef}
              type="file"
              accept=".pdf,.docx,.txt"
              onChange={onUpload}
              className="block text-[13px] text-charcoal-700
                file:mr-3 file:px-4 file:py-2 file:rounded-[6px] file:border-0
                file:bg-steel-700 file:text-white file:font-medium file:cursor-pointer"
            />
            {uploading && (
              <span className="text-[13px] text-charcoal-500">Uploading…</span>
            )}
          </div>
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="Documents in this opportunity" />
        <CardBody className="!p-0">
          {docs === null ? (
            <div className="p-6 flex flex-col gap-2">
              {[0, 1].map((i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          ) : (
            <DataTable
              columns={[
                { key: "name", header: "Name", render: (d) => <span className="font-medium">{d.name}</span> },
                { key: "type", header: "Type", render: (d) => d.doc_type },
                { key: "pages", header: "Pages", align: "right", render: (d) => d.page_count ?? "—" },
                {
                  key: "size",
                  header: "Size",
                  align: "right",
                  render: (d) => `${(d.size_bytes / 1024).toFixed(1)} KB`,
                },
                {
                  key: "status",
                  header: "Status",
                  render: (d) => (
                    <StatusPill tone={statusTone(d.status)}>{d.status}</StatusPill>
                  ),
                },
                {
                  key: "uploaded",
                  header: "Uploaded",
                  render: (d) => formatDateTime(d.uploaded_at),
                },
              ]}
              rows={docs}
              emptyState={
                <div className="p-10 text-center text-charcoal-500">
                  <div className="text-h3 text-charcoal-900">No documents yet</div>
                  <p className="mt-1 text-[14px]">
                    Upload an RFP, PWS, or capture note to start producing intelligence.
                  </p>
                </div>
              }
            />
          )}
        </CardBody>
      </Card>
    </div>
  );
}
