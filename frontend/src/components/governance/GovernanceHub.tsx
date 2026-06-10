"use client";

import clsx from "clsx";
import { useCallback, useEffect, useState } from "react";
import { apiRequest } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type {
  AssumptionPanelData,
  DeliverableReview,
  GovernanceComment,
  HumanOverride,
} from "@/lib/types";
import {
  GOVERNED_MODULES,
  REVIEWABLE_MODULES,
} from "@/lib/governance";
import { Card, CardBody, CardHeader } from "@/components/ds/Card";
import { CommentsPanel, type MemberOption } from "./CommentsPanel";
import { ReviewPanel } from "./ReviewPanel";
import { ApprovalPanel } from "./ApprovalPanel";
import { AssumptionsPanel } from "./AssumptionsPanel";
import { FeedbackPanel } from "./FeedbackPanel";

type TabId = "comments" | "review" | "approvals" | "assumptions" | "feedback";

/**
 * Collaboration & Governance hub, mounted beneath every governed briefing.
 * MissionIQ generates intelligence; humans make decisions — every judgment
 * recorded here lives alongside the original AI output, never over it.
 */
export function GovernanceHub({
  opportunityId,
  moduleId,
  output,
}: {
  opportunityId: string;
  moduleId: string;
  output: Record<string, unknown> | null;
}) {
  const { currentWorkspaceId } = useAuth();
  const governed = (GOVERNED_MODULES as readonly string[]).includes(moduleId);
  const reviewable = (REVIEWABLE_MODULES as readonly string[]).includes(moduleId);

  const [tab, setTab] = useState<TabId>("comments");
  const [comments, setComments] = useState<GovernanceComment[]>([]);
  const [members, setMembers] = useState<MemberOption[]>([]);
  const [review, setReview] = useState<DeliverableReview | null>(null);
  const [history, setHistory] = useState<DeliverableReview[]>([]);
  const [assumptions, setAssumptions] = useState<AssumptionPanelData | null>(null);
  const [overrides, setOverrides] = useState<HumanOverride[]>([]);

  const reloadComments = useCallback(async () => {
    const r = await apiRequest<GovernanceComment[]>(
      `/opportunities/${opportunityId}/comments?module_id=${encodeURIComponent(moduleId)}`,
    );
    setComments(r);
  }, [opportunityId, moduleId]);

  const reloadReview = useCallback(async () => {
    if (!reviewable) return;
    const [r, h] = await Promise.all([
      apiRequest<DeliverableReview>(
        `/opportunities/${opportunityId}/modules/${moduleId}/review`,
      ),
      apiRequest<DeliverableReview[]>(
        `/opportunities/${opportunityId}/modules/${moduleId}/review/history`,
      ),
    ]);
    setReview(r);
    setHistory(h);
  }, [opportunityId, moduleId, reviewable]);

  const reloadAssumptions = useCallback(async () => {
    const r = await apiRequest<AssumptionPanelData>(
      `/opportunities/${opportunityId}/modules/${moduleId}/assumptions`,
    );
    setAssumptions(r);
  }, [opportunityId, moduleId]);

  const reloadOverrides = useCallback(async () => {
    const r = await apiRequest<HumanOverride[]>(
      `/opportunities/${opportunityId}/overrides?module_id=${encodeURIComponent(moduleId)}`,
    );
    setOverrides(r);
  }, [opportunityId, moduleId]);

  useEffect(() => {
    if (!governed) return;
    reloadComments().catch(() => setComments([]));
    reloadReview().catch(() => setReview(null));
    reloadAssumptions().catch(() => setAssumptions(null));
    reloadOverrides().catch(() => setOverrides([]));
  }, [governed, reloadComments, reloadReview, reloadAssumptions, reloadOverrides]);

  useEffect(() => {
    if (!governed || !currentWorkspaceId) return;
    apiRequest<MemberOption[]>(`/workspaces/${currentWorkspaceId}/members`)
      .then((rows) => setMembers(rows))
      .catch(() => setMembers([]));
  }, [governed, currentWorkspaceId]);

  if (!governed) return null;

  const openComments = comments.filter(
    (c) => !c.parent_comment_id && c.status === "open",
  ).length;
  const assumptionCount = assumptions?.assumptions.length ?? 0;
  const moduleOverrideCount = overrides.filter((o) => o.module_id === moduleId).length;

  const tabs: { id: TabId; label: string; count?: number }[] = [
    { id: "comments", label: "Comments", count: openComments },
    ...(reviewable
      ? ([
          { id: "review", label: "Review" },
          { id: "approvals", label: "Approvals" },
        ] as { id: TabId; label: string }[])
      : []),
    { id: "assumptions", label: "Assumptions", count: assumptionCount },
    { id: "feedback", label: "Feedback", count: moduleOverrideCount },
  ];

  return (
    <Card>
      <CardHeader
        eyebrow="Collaboration & Governance"
        title="Team review, validation & decision record"
        subtitle="Human judgment is recorded alongside MissionIQ's original output — never over it. Every action is audited."
      />
      <CardBody>
        <div className="flex flex-wrap gap-1.5 border-b border-charcoal-100 pb-3 mb-4">
          {tabs.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={clsx(
                "inline-flex items-center gap-1.5 rounded-[6px] px-3 py-1.5 text-[13px] font-medium transition-colors",
                tab === t.id
                  ? "bg-steel-700 text-white"
                  : "text-charcoal-700 hover:bg-charcoal-100",
              )}
            >
              {t.label}
              {typeof t.count === "number" && t.count > 0 && (
                <span
                  className={clsx(
                    "rounded-full px-1.5 text-[11px]",
                    tab === t.id ? "bg-white/20" : "bg-charcoal-100 text-charcoal-700",
                  )}
                >
                  {t.count}
                </span>
              )}
            </button>
          ))}
        </div>

        {tab === "comments" && (
          <CommentsPanel
            opportunityId={opportunityId}
            moduleId={moduleId}
            comments={comments}
            members={members}
            onChanged={reloadComments}
          />
        )}
        {tab === "review" && reviewable && (
          <ReviewPanel
            opportunityId={opportunityId}
            moduleId={moduleId}
            review={review}
            onChanged={reloadReview}
          />
        )}
        {tab === "approvals" && reviewable && <ApprovalPanel history={history} />}
        {tab === "assumptions" && (
          <AssumptionsPanel
            opportunityId={opportunityId}
            moduleId={moduleId}
            panel={assumptions}
            onChanged={reloadAssumptions}
          />
        )}
        {tab === "feedback" && (
          <FeedbackPanel
            opportunityId={opportunityId}
            moduleId={moduleId}
            output={output}
            overrides={overrides}
            onChanged={reloadOverrides}
          />
        )}
      </CardBody>
    </Card>
  );
}
