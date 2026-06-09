export function formatCurrencyCents(cents: number | null | undefined): string {
  if (cents == null) return "—";
  const dollars = cents / 100;
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(dollars);
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function daysUntil(iso: string | null | undefined): number | null {
  if (!iso) return null;
  const diff = new Date(iso).getTime() - Date.now();
  return Math.floor(diff / (1000 * 60 * 60 * 24));
}

const STAGE_LABEL: Record<string, string> = {
  identification: "Identification",
  qualification: "Qualification",
  pursue: "Pursue",
  capture: "Capture",
  proposal: "Proposal",
  submitted: "Submitted",
  awarded: "Awarded",
  lost: "Lost",
  "no-bid": "No-Bid",
};

export function captureStageLabel(stage: string): string {
  return STAGE_LABEL[stage] ?? stage;
}
