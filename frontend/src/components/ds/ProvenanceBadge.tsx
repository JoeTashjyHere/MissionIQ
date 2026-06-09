import clsx from "clsx";
import { Bot, Brain, Cable, Globe2, UserRound, type LucideIcon } from "lucide-react";

/**
 * Data provenance chip. Every piece of information in MissionIQ identifies
 * its source; this badge renders the five platform provenance categories
 * consistently wherever data appears.
 */
export type ProvenanceSource =
  | "user_upload"
  | "connector"
  | "public_market_intel"
  | "historical_memory"
  | "generated_intelligence";

const META: Record<
  ProvenanceSource,
  { label: string; icon: LucideIcon; className: string }
> = {
  user_upload: {
    label: "User Uploaded",
    icon: UserRound,
    className: "bg-charcoal-100 text-charcoal-700",
  },
  connector: {
    label: "Connector Ingested",
    icon: Cable,
    className: "bg-steel-700/10 text-steel-700",
  },
  public_market_intel: {
    label: "Public Market Intelligence",
    icon: Globe2,
    className: "bg-teal-100 text-teal-700",
  },
  historical_memory: {
    label: "Historical Memory",
    icon: Brain,
    className: "bg-navy-700/10 text-navy-700",
  },
  generated_intelligence: {
    label: "Generated Intelligence",
    icon: Bot,
    className: "bg-status-amberBg text-status-amber",
  },
};

export function ProvenanceBadge({
  source,
  detail,
  className,
}: {
  source: ProvenanceSource;
  /** Optional qualifier, e.g. the connector provider name ("Salesforce"). */
  detail?: string | null;
  className?: string;
}) {
  const meta = META[source];
  const Icon = meta.icon;
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1 rounded-[6px] px-2 py-0.5 text-[11px] font-medium whitespace-nowrap",
        meta.className,
        className,
      )}
      title={detail ? `${meta.label} · ${detail}` : meta.label}
    >
      <Icon className="h-3 w-3 shrink-0" strokeWidth={2} />
      {detail ? `${meta.label} · ${detail}` : meta.label}
    </span>
  );
}
