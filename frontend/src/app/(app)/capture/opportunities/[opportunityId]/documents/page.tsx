"use client";

import { use, useEffect, useRef, useState } from "react";
import { apiRequest, getAccessToken } from "@/lib/api";
import type { DocumentRecord, DocumentStatus } from "@/lib/types";
import { PageHeader } from "@/components/PageHeader";
import { Card, CardBody, CardHeader } from "@/components/ds/Card";
import { DataTable } from "@/components/ds/DataTable";
import { StatusPill } from "@/components/ds/StatusPill";
import { Select } from "@/components/ds/Select";
import { Skeleton } from "@/components/ds/Skeleton";
import { ProgressBar } from "@/components/ds/ProgressBar";
import { ProvenanceBadge } from "@/components/ds/ProvenanceBadge";
import { EmptyState } from "@/components/ds/EmptyState";
import { formatDateTime } from "@/lib/format";
import { FileText, UploadCloud } from "lucide-react";

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

const STATUS_LABEL: Record<DocumentStatus, string> = {
  uploaded: "Queued",
  parsing: "Parsing",
  chunking: "Chunking",
  embedding: "Embedding",
  ready: "Ready",
  failed: "Failed",
};

const STATUS_HELP: Record<DocumentStatus, string> = {
  uploaded: "Queued for processing.",
  parsing: "Extracting text and detecting structure.",
  chunking: "Segmenting into evidence-grade chunks.",
  embedding: "Generating embeddings for retrieval.",
  ready: "Indexed and available for analysis.",
  failed: "Processing failed. See error and re-upload.",
};

function statusTone(s: DocumentStatus): "green" | "amber" | "red" | "neutral" {
  if (s === "ready") return "green";
  if (s === "failed") return "red";
  return "amber";
}

function progressTone(s: DocumentStatus): "steel" | "green" | "amber" | "red" {
  if (s === "ready") return "green";
  if (s === "failed") return "red";
  return "steel";
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
  const [uploadError, setUploadError] = useState<string | null>(null);
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
    }, 2500);
    return () => clearInterval(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [opportunityId]);

  const onUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setUploadError(null);
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
        let detail = `Upload failed (HTTP ${resp.status})`;
        try {
          const body = await resp.json();
          detail = body?.detail ?? body?.title ?? detail;
        } catch {
          /* ignore */
        }
        throw new Error(detail);
      }
      await refresh();
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : "Upload failed.");
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  const hasDocs = (docs?.length ?? 0) > 0;
  const readyCount = (docs ?? []).filter((d) => d.status === "ready").length;
  const processingCount = (docs ?? []).filter(
    (d) => d.status !== "ready" && d.status !== "failed",
  ).length;
  const failedCount = (docs ?? []).filter((d) => d.status === "failed").length;

  return (
    <div>
      <PageHeader
        eyebrow="Capture Intelligence · Documents"
        title="Opportunity documents"
        subtitle="Upload RFPs, PWS/SOW/SOO, evaluation criteria, capture notes, and supporting docs. MissionIQ parses, chunks, and indexes each document so the Assistant and intelligence modules can ground answers in your sources."
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
              accept=".pdf,.docx,.txt,.md"
              onChange={onUpload}
              disabled={uploading}
              className="block text-[13px] text-charcoal-700
                file:mr-3 file:px-4 file:py-2 file:rounded-[6px] file:border-0
                file:bg-steel-700 file:text-white file:font-medium file:cursor-pointer
                disabled:opacity-60"
            />
            {uploading && (
              <span className="text-[13px] text-charcoal-500">Uploading…</span>
            )}
          </div>
          {uploadError && (
            <div className="mt-3 rounded-md bg-status-redBg border border-status-red/30 text-status-red text-[13px] px-3 py-2">
              {uploadError}
            </div>
          )}
          {hasDocs && (
            <div className="mt-4 flex flex-wrap gap-4 text-[12px] text-charcoal-500">
              <span>
                <span className="font-medium text-status-green">{readyCount}</span> ready
              </span>
              <span>
                <span className="font-medium text-status-amber">{processingCount}</span>{" "}
                processing
              </span>
              {failedCount > 0 && (
                <span>
                  <span className="font-medium text-status-red">{failedCount}</span> failed
                </span>
              )}
            </div>
          )}
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="Documents in this opportunity" />
        <CardBody className="!p-0">
          {docs === null ? (
            <div className="p-6 flex flex-col gap-2">
              {[0, 1, 2].map((i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : docs.length === 0 ? (
            <EmptyState
              icon={<UploadCloud />}
              title="No documents yet"
              description="Upload an RFP, PWS, SOW, or Sections L & M to start producing source-cited capture intelligence."
            />
          ) : (
            <DataTable
              columns={[
                {
                  key: "name",
                  header: "Name",
                  render: (d) => (
                    <div className="flex items-start gap-2">
                      <FileText
                        className="mt-0.5 h-4 w-4 text-charcoal-500 shrink-0"
                        aria-hidden
                      />
                      <div className="min-w-0">
                        <div className="font-medium text-charcoal-900 truncate">
                          {d.name}
                        </div>
                        <div className="text-[11px] text-charcoal-500">
                          {d.doc_type} · {(d.size_bytes / 1024).toFixed(1)} KB
                        </div>
                      </div>
                    </div>
                  ),
                },
                {
                  key: "source",
                  header: "Source",
                  render: (d) => (
                    <ProvenanceBadge
                      source={d.source_type === "connector" ? "connector" : "user_upload"}
                    />
                  ),
                },
                {
                  key: "pages",
                  header: "Pages",
                  align: "right",
                  render: (d) => d.page_count ?? "—",
                },
                {
                  key: "chunks",
                  header: "Chunks",
                  align: "right",
                  render: (d) => d.chunk_count ?? "—",
                },
                {
                  key: "status",
                  header: "Processing",
                  render: (d) => (
                    <div className="min-w-[180px]">
                      <div className="flex items-center gap-2">
                        <StatusPill tone={statusTone(d.status)}>
                          {STATUS_LABEL[d.status]}
                        </StatusPill>
                        <span className="text-[11px] text-charcoal-500">
                          {d.progress_pct}%
                        </span>
                      </div>
                      <div className="mt-1.5">
                        <ProgressBar
                          value={d.progress_pct}
                          tone={progressTone(d.status)}
                          ariaLabel={`${d.name} processing progress`}
                        />
                      </div>
                      <div className="mt-1 text-[11px] text-charcoal-500">
                        {STATUS_HELP[d.status]}
                      </div>
                      {d.status === "failed" && d.error_message && (
                        <div className="mt-1 text-[11px] text-status-red truncate">
                          {d.error_message}
                        </div>
                      )}
                    </div>
                  ),
                },
                {
                  key: "uploaded",
                  header: "Uploaded",
                  render: (d) => formatDateTime(d.uploaded_at),
                },
              ]}
              rows={docs}
            />
          )}
        </CardBody>
      </Card>
    </div>
  );
}
