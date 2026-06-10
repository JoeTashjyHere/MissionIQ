import type { PursuitOutcomeKind } from "@/lib/types";

export const OUTCOME_LABEL: Record<string, string> = {
  won: "Won",
  lost: "Lost",
  no_bid: "No-Bid",
  cancelled: "Cancelled",
  withdrawn: "Withdrawn",
};

export const OUTCOME_OPTIONS: { value: PursuitOutcomeKind; label: string }[] = [
  { value: "won", label: "Won" },
  { value: "lost", label: "Lost" },
  { value: "no_bid", label: "No-Bid" },
  { value: "cancelled", label: "Cancelled" },
  { value: "withdrawn", label: "Withdrawn" },
];

export function outcomeTone(
  outcome: string,
): "green" | "amber" | "red" | "neutral" {
  if (outcome === "won") return "green";
  if (outcome === "lost") return "red";
  if (outcome === "no_bid") return "amber";
  return "neutral";
}
