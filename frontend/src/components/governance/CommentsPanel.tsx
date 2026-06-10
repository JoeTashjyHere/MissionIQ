"use client";

import { useMemo, useState } from "react";
import { apiRequest, ApiError } from "@/lib/api";
import type { GovernanceComment, Uuid } from "@/lib/types";
import { hasCapability, useWorkspaceRole } from "@/lib/governance";
import { Button } from "@/components/ds/Button";
import { StatusPill } from "@/components/ds/StatusPill";
import { formatDateTime } from "@/lib/format";
import { AtSign, CheckCircle2, CornerDownRight, RotateCcw } from "lucide-react";

export interface MemberOption {
  user_id: Uuid;
  user_full_name: string;
}

function CommentBody({
  comment,
  members,
}: {
  comment: GovernanceComment;
  members: MemberOption[];
}) {
  const mentioned = comment.mentions
    .map((id) => members.find((m) => m.user_id === id)?.user_full_name)
    .filter(Boolean) as string[];
  return (
    <div>
      <div className="flex items-center gap-2 text-[12px] text-charcoal-500">
        <span className="font-semibold text-charcoal-900">{comment.author_name}</span>
        <span>{formatDateTime(comment.created_at)}</span>
      </div>
      <p className="mt-1 text-[13px] text-charcoal-700 whitespace-pre-wrap">
        {comment.body}
      </p>
      {mentioned.length > 0 && (
        <div className="mt-1.5 flex flex-wrap gap-1.5">
          {mentioned.map((name) => (
            <span
              key={name}
              className="inline-flex items-center gap-1 rounded-full bg-steel-700/10 px-2 py-0.5 text-[11px] font-medium text-steel-700"
            >
              <AtSign className="h-3 w-3" />
              {name}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

function ComposeBox({
  placeholder,
  members,
  busy,
  onSubmit,
}: {
  placeholder: string;
  members: MemberOption[];
  busy: boolean;
  onSubmit: (body: string, mentions: Uuid[]) => Promise<void>;
}) {
  const [body, setBody] = useState("");
  const [mentions, setMentions] = useState<Uuid[]>([]);
  const [error, setError] = useState<string | null>(null);

  const submit = async () => {
    setError(null);
    try {
      await onSubmit(body.trim(), mentions);
      setBody("");
      setMentions([]);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Failed to post comment.");
    }
  };

  return (
    <div className="flex flex-col gap-2">
      <textarea
        value={body}
        onChange={(e) => setBody(e.target.value)}
        placeholder={placeholder}
        rows={2}
        className="w-full rounded-[6px] border border-charcoal-300 bg-white px-3 py-2 text-[13px] text-charcoal-900 focus-visible:border-steel-500"
      />
      <div className="flex items-center justify-between gap-2">
        <select
          value=""
          onChange={(e) => {
            const id = e.target.value as Uuid;
            if (id && !mentions.includes(id)) setMentions([...mentions, id]);
          }}
          className="h-8 rounded-[6px] border border-charcoal-300 bg-white px-2 text-[12px] text-charcoal-700"
        >
          <option value="">@ Mention…</option>
          {members.map((m) => (
            <option key={m.user_id} value={m.user_id}>
              {m.user_full_name}
            </option>
          ))}
        </select>
        <Button size="sm" onClick={submit} loading={busy} disabled={!body.trim()}>
          Comment
        </Button>
      </div>
      {mentions.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {mentions.map((id) => {
            const name = members.find((m) => m.user_id === id)?.user_full_name ?? id;
            return (
              <button
                key={id}
                onClick={() => setMentions(mentions.filter((x) => x !== id))}
                className="inline-flex items-center gap-1 rounded-full bg-steel-700/10 px-2 py-0.5 text-[11px] font-medium text-steel-700 hover:bg-steel-700/20"
                title="Remove mention"
              >
                <AtSign className="h-3 w-3" />
                {name} ×
              </button>
            );
          })}
        </div>
      )}
      {error && <p className="text-[12px] text-status-red">{error}</p>}
    </div>
  );
}

export function CommentsPanel({
  opportunityId,
  moduleId,
  comments,
  members,
  onChanged,
}: {
  opportunityId: string;
  moduleId: string;
  comments: GovernanceComment[];
  members: MemberOption[];
  onChanged: () => Promise<void>;
}) {
  const role = useWorkspaceRole();
  const canComment = hasCapability(role, "comment.create");
  const canResolve = hasCapability(role, "comment.resolve");
  const [busy, setBusy] = useState(false);
  const [replyTo, setReplyTo] = useState<Uuid | null>(null);
  const [showResolved, setShowResolved] = useState(false);

  const threads = useMemo(() => {
    const roots = comments.filter((c) => !c.parent_comment_id);
    const byParent = new Map<Uuid, GovernanceComment[]>();
    for (const c of comments) {
      if (c.parent_comment_id) {
        const list = byParent.get(c.parent_comment_id) ?? [];
        list.push(c);
        byParent.set(c.parent_comment_id, list);
      }
    }
    return roots
      .filter((r) => showResolved || r.status === "open")
      .map((root) => ({ root, replies: byParent.get(root.id) ?? [] }));
  }, [comments, showResolved]);

  const post = async (body: string, mentions: Uuid[], parentId: Uuid | null) => {
    setBusy(true);
    try {
      await apiRequest(`/opportunities/${opportunityId}/comments`, {
        method: "POST",
        body: {
          target_module_id: moduleId,
          body,
          parent_comment_id: parentId,
          mentions,
        },
      });
      setReplyTo(null);
      await onChanged();
    } finally {
      setBusy(false);
    }
  };

  const setStatus = async (commentId: Uuid, resolved: boolean) => {
    setBusy(true);
    try {
      await apiRequest(
        `/opportunities/${opportunityId}/comments/${commentId}/${resolved ? "resolve" : "reopen"}`,
        { method: "POST", body: {} },
      );
      await onChanged();
    } finally {
      setBusy(false);
    }
  };

  const resolvedCount = comments.filter(
    (c) => !c.parent_comment_id && c.status === "resolved",
  ).length;

  return (
    <div className="flex flex-col gap-4">
      {canComment && (
        <ComposeBox
          placeholder="Add a comment for the team — every comment is audited."
          members={members}
          busy={busy}
          onSubmit={(body, mentions) => post(body, mentions, null)}
        />
      )}
      {resolvedCount > 0 && (
        <button
          onClick={() => setShowResolved(!showResolved)}
          className="self-start text-[12px] text-steel-700 underline hover:text-charcoal-900"
        >
          {showResolved ? "Hide" : "Show"} {resolvedCount} resolved thread
          {resolvedCount === 1 ? "" : "s"}
        </button>
      )}
      {threads.length === 0 && (
        <p className="text-[13px] text-charcoal-500">
          No open comments on this briefing yet.
        </p>
      )}
      {threads.map(({ root, replies }) => (
        <div
          key={root.id}
          className="rounded-md border border-charcoal-100 bg-white p-3"
        >
          <div className="flex items-start justify-between gap-2">
            <CommentBody comment={root} members={members} />
            <div className="flex items-center gap-2 shrink-0">
              {root.status === "resolved" ? (
                <StatusPill tone="green">Resolved</StatusPill>
              ) : (
                <StatusPill tone="amber">Open</StatusPill>
              )}
            </div>
          </div>
          {root.status === "resolved" && root.resolved_by_name && (
            <p className="mt-1.5 text-[11px] text-charcoal-500">
              Resolved by {root.resolved_by_name}
              {root.resolved_at ? ` · ${formatDateTime(root.resolved_at)}` : ""}
            </p>
          )}
          {replies.map((reply) => (
            <div
              key={reply.id}
              className="mt-3 flex gap-2 border-l-2 border-charcoal-100 pl-3"
            >
              <CornerDownRight className="h-3.5 w-3.5 mt-1 text-charcoal-300 shrink-0" />
              <CommentBody comment={reply} members={members} />
            </div>
          ))}
          <div className="mt-3 flex items-center gap-3">
            {canComment && root.status === "open" && (
              <button
                onClick={() => setReplyTo(replyTo === root.id ? null : root.id)}
                className="text-[12px] font-medium text-steel-700 hover:text-charcoal-900"
              >
                Reply
              </button>
            )}
            {canResolve && root.status === "open" && (
              <button
                onClick={() => setStatus(root.id, true)}
                className="inline-flex items-center gap-1 text-[12px] font-medium text-status-green hover:opacity-80"
              >
                <CheckCircle2 className="h-3.5 w-3.5" /> Resolve
              </button>
            )}
            {canResolve && root.status === "resolved" && (
              <button
                onClick={() => setStatus(root.id, false)}
                className="inline-flex items-center gap-1 text-[12px] font-medium text-charcoal-700 hover:text-charcoal-900"
              >
                <RotateCcw className="h-3.5 w-3.5" /> Reopen
              </button>
            )}
          </div>
          {replyTo === root.id && (
            <div className="mt-3">
              <ComposeBox
                placeholder={`Reply to ${root.author_name}…`}
                members={members}
                busy={busy}
                onSubmit={(body, mentions) => post(body, mentions, root.id)}
              />
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
