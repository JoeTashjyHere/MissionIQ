"use client";

/**
 * Collaboration & Governance helpers: the frontend mirror of the backend
 * capability layer (app/core/rbac.py). Server-side enforcement is
 * authoritative — this exists only to role-gate UI affordances.
 */
import { useAuth } from "@/lib/auth-context";
import type { ReviewStatus, WorkspaceRole } from "@/lib/types";

export const ROLE_ORDER: WorkspaceRole[] = [
  "viewer",
  "contributor",
  "reviewer",
  "approver",
  "administrator",
];

export const ROLE_DESCRIPTIONS: Record<WorkspaceRole, string> = {
  viewer: "Read-only access to all intelligence and governance records.",
  contributor: "Generate intelligence, comment, and submit deliverables for review.",
  reviewer: "Contributor, plus record review notes on deliverables in review.",
  approver:
    "Reviewer, plus approve/reject deliverables, override recommendations, and validate assumptions.",
  administrator: "Full control, including team and workspace management.",
};

const CAPABILITY_MIN_ROLE = {
  "intelligence.generate": "contributor",
  "outcome.record": "contributor",
  "comment.create": "contributor",
  "comment.resolve": "contributor",
  "review.submit": "contributor",
  "review.note": "reviewer",
  "review.decide": "approver",
  "decision.override": "approver",
  "assumption.validate": "approver",
  "member.manage": "administrator",
  "workspace.manage": "administrator",
} as const satisfies Record<string, WorkspaceRole>;

export type Capability = keyof typeof CAPABILITY_MIN_ROLE;

export function hasCapability(
  role: WorkspaceRole | null | undefined,
  capability: Capability,
): boolean {
  if (!role) return false;
  const rank = ROLE_ORDER.indexOf(role);
  if (rank < 0) return false;
  return rank >= ROLE_ORDER.indexOf(CAPABILITY_MIN_ROLE[capability]);
}

/** The current user's role in the active workspace. */
export function useWorkspaceRole(): WorkspaceRole | null {
  const { memberships, currentWorkspaceId } = useAuth();
  const membership = memberships.find((m) => m.workspace_id === currentWorkspaceId);
  return membership?.role ?? null;
}

// ── Governed modules ─────────────────────────────────────────────────────────

export const GOVERNED_MODULES = [
  "capture.customer_dna",
  "capture.company_dna",
  "capture.capability_match",
  "capture.win_strategy",
  "capture.executive_brief",
  "capture.gate_review",
  "capture.bid_decision",
  "capture.outcome_intelligence",
] as const;

export const REVIEWABLE_MODULES = [
  "capture.win_strategy",
  "capture.executive_brief",
  "capture.gate_review",
  "capture.bid_decision",
] as const;

export const MODULE_LABELS: Record<string, string> = {
  "capture.customer_dna": "Customer DNA",
  "capture.company_dna": "Company DNA",
  "capture.capability_match": "Capability Match",
  "capture.win_strategy": "Win Strategy",
  "capture.executive_brief": "Executive Brief",
  "capture.gate_review": "Gate Review",
  "capture.bid_decision": "Bid Decision",
  "capture.outcome_intelligence": "Outcome Intelligence",
};

// ── Review workflow display ──────────────────────────────────────────────────

export const REVIEW_STATUS_LABEL: Record<ReviewStatus, string> = {
  draft: "Draft",
  in_review: "In Review",
  approved: "Approved",
  rejected: "Rejected",
  archived: "Archived",
};

export function reviewStatusTone(
  status: ReviewStatus,
): "green" | "amber" | "red" | "info" | "neutral" {
  switch (status) {
    case "approved":
      return "green";
    case "in_review":
      return "amber";
    case "rejected":
      return "red";
    case "draft":
      return "info";
    default:
      return "neutral";
  }
}
