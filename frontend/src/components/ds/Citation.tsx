"use client";

import { useState } from "react";
import clsx from "clsx";
import type { Citation as CitationType } from "@/lib/types";

export function CitationChip({
  index,
  citation,
  onOpen,
}: {
  index: number;
  citation: CitationType;
  onOpen?: (c: CitationType) => void;
}) {
  const [open, setOpen] = useState(false);
  const label =
    citation.type === "document_chunk"
      ? `${citation.document_name} · p.${citation.page_start ?? "?"}${citation.section_path ? ` · ${citation.section_path}` : ""}`
      : `${citation.source_id.toUpperCase()} · ${citation.title}`;
  const snippet =
    citation.type === "document_chunk" ? citation.snippet : citation.title;
  return (
    <span
      className="relative inline-block"
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      onFocus={() => setOpen(true)}
      onBlur={() => setOpen(false)}
    >
      <button
        type="button"
        onClick={() => onOpen?.(citation)}
        className="font-mono text-[12px] text-steel-700 hover:underline ml-0.5"
      >
        [{index}]
      </button>
      {open && (
        <span
          role="tooltip"
          className={clsx(
            "absolute z-50 left-0 top-full mt-1 w-[360px] rounded-md border border-charcoal-300",
            "bg-white shadow-elevated p-3 text-[12px] text-charcoal-700",
          )}
        >
          <div className="text-[11px] uppercase tracking-wide font-semibold text-charcoal-500 mb-1">
            {citation.type === "document_chunk" ? "Source document" : "Market intelligence"}
          </div>
          <div className="font-medium text-charcoal-900 mb-1">{label}</div>
          <div className="text-charcoal-700 line-clamp-5 whitespace-pre-line">
            {snippet}
          </div>
        </span>
      )}
    </span>
  );
}

export function CitationsRow({ citations }: { citations: CitationType[] }) {
  if (!citations.length) {
    return (
      <div className="text-[12px] text-status-amber border border-status-amber/30 bg-status-amberBg rounded-md px-3 py-2">
        No source citations were attached to this output. Treat findings as unverified.
      </div>
    );
  }
  return (
    <div className="flex flex-wrap items-center gap-1.5 text-[12px] text-charcoal-500">
      <span className="font-medium uppercase tracking-wide text-[11px]">Sources:</span>
      {citations.map((c, i) => (
        <CitationChip key={(c as { id: string }).id + i} index={i + 1} citation={c} />
      ))}
    </div>
  );
}
