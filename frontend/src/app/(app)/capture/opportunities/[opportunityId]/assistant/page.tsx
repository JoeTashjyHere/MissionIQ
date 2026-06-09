"use client";

import { use, useCallback, useEffect, useRef, useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { apiRequest, ApiError } from "@/lib/api";
import type {
  ChatMessage,
  ChatThread,
  DocumentRecord,
} from "@/lib/types";
import { PageHeader } from "@/components/PageHeader";
import { Card, CardBody, CardHeader } from "@/components/ds/Card";
import { Button } from "@/components/ds/Button";
import { Textarea } from "@/components/ds/Input";
import { StatusPill } from "@/components/ds/StatusPill";
import { CitationsRow } from "@/components/ds/Citation";
import { Skeleton } from "@/components/ds/Skeleton";
import { AlertTriangle, MessagesSquare } from "lucide-react";

const STARTERS = [
  "Summarize the major requirements.",
  "What are the key evaluation drivers?",
  "Where are our biggest capability gaps?",
  "What capture questions are still unanswered?",
  "What are the surfaced risks and how should we mitigate them?",
];

export default function AssistantPage({
  params,
}: {
  params: Promise<{ opportunityId: string }>;
}) {
  const { opportunityId } = use(params);
  const { currentWorkspaceId } = useAuth();
  const [thread, setThread] = useState<ChatThread | null>(null);
  const [messages, setMessages] = useState<ChatMessage[] | null>(null);
  const [docs, setDocs] = useState<DocumentRecord[] | null>(null);
  const [content, setContent] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  const ensureThread = useCallback(async () => {
    if (!currentWorkspaceId) return null;
    const existing = await apiRequest<ChatThread[]>(
      `/chat/threads?workspace_id=${currentWorkspaceId}&opportunity_id=${opportunityId}`,
    );
    if (existing.length > 0) return existing[0];
    return await apiRequest<ChatThread>("/chat/threads", {
      method: "POST",
      body: {
        workspace_id: currentWorkspaceId,
        opportunity_id: opportunityId,
        title: "Opportunity Assistant",
      },
    });
  }, [currentWorkspaceId, opportunityId]);

  useEffect(() => {
    (async () => {
      const t = await ensureThread();
      if (!t) return;
      setThread(t);
      const [msgs, ds] = await Promise.all([
        apiRequest<ChatMessage[]>(`/chat/threads/${t.id}/messages`),
        apiRequest<DocumentRecord[]>(
          `/opportunities/${opportunityId}/documents`,
        ),
      ]);
      setMessages(msgs);
      setDocs(ds);
    })().catch((e) =>
      setError(e instanceof ApiError ? e.detail : "Failed to load chat."),
    );
  }, [ensureThread, opportunityId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = async (text: string) => {
    if (!thread || !text.trim()) return;
    setSending(true);
    setError(null);
    try {
      const resp = await apiRequest<{
        user_message: ChatMessage;
        assistant_message: ChatMessage;
      }>(`/chat/threads/${thread.id}/messages`, {
        method: "POST",
        body: { content: text },
      });
      setMessages((m) => [
        ...(m ?? []),
        resp.user_message,
        resp.assistant_message,
      ]);
      setContent("");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Send failed.");
    } finally {
      setSending(false);
    }
  };

  const readyDocCount = (docs ?? []).filter((d) => d.status === "ready").length;
  const hasNoReadyDocs = docs !== null && readyDocCount === 0;

  return (
    <div>
      <PageHeader
        eyebrow="Capture Intelligence"
        title="Intelligence Assistant"
        subtitle="Ask grounded questions about this opportunity. The Assistant answers only from your uploaded documents and linked market intelligence. Every answer carries source citations."
      />

      {hasNoReadyDocs && (
        <div className="mb-4 rounded-md bg-status-amberBg border border-status-amber/30 text-status-amber text-[13px] px-3 py-2 flex items-start gap-2">
          <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
          <div>
            No documents are indexed yet. The Assistant will refuse to answer
            until at least one document for this opportunity reaches the{" "}
            <span className="font-medium">ready</span> state. Upload one on the
            Documents tab.
          </div>
        </div>
      )}

      <Card>
        <CardHeader
          title="Conversation"
          subtitle={thread ? `Thread · ${thread.id.slice(0, 8)}` : "Initializing…"}
          actions={
            docs !== null ? (
              <span className="text-[12px] text-charcoal-500">
                {readyDocCount} indexed
              </span>
            ) : null
          }
        />
        <CardBody className="!p-0">
          <div className="px-6 py-4 max-h-[60vh] min-h-[40vh] overflow-y-auto flex flex-col gap-4">
            {messages === null ? (
              <div className="flex flex-col gap-3">
                <Skeleton className="h-16 w-3/4" />
                <Skeleton className="h-16 w-3/4 self-end" />
              </div>
            ) : messages.length === 0 ? (
              <div className="text-charcoal-500 text-[14px]">
                <div className="flex items-center gap-2 text-charcoal-700 mb-2">
                  <MessagesSquare className="h-4 w-4" />
                  <span className="font-medium">Start a grounded conversation</span>
                </div>
                <p className="mb-3 text-[13px]">
                  Ask a question, or try one of these:
                </p>
                <div className="flex flex-col gap-1.5">
                  {STARTERS.map((s) => (
                    <button
                      key={s}
                      className="text-left text-[13px] text-steel-700 hover:underline disabled:text-charcoal-300 disabled:no-underline disabled:cursor-not-allowed"
                      onClick={() => send(s)}
                      disabled={hasNoReadyDocs || sending}
                    >
                      → {s}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              messages.map((m) => (
                <div
                  key={m.id}
                  className={`max-w-[80%] ${m.role === "user" ? "self-end" : "self-start"}`}
                >
                  <div
                    className={`rounded-md px-4 py-3 text-[14px] ${
                      m.role === "user"
                        ? "bg-navy-900 text-white"
                        : m.status === "insufficient_context"
                          ? "bg-status-amberBg border border-status-amber/30 text-charcoal-900"
                          : m.status === "error"
                            ? "bg-status-redBg border border-status-red/30 text-charcoal-900"
                            : "bg-white border border-charcoal-300 text-charcoal-900"
                    }`}
                  >
                    <div className="whitespace-pre-wrap">{m.content}</div>
                    {m.role === "assistant" && (
                      <div className="mt-2 flex items-center gap-2 flex-wrap">
                        <StatusPill
                          tone={
                            m.status === "ok"
                              ? "green"
                              : m.status === "insufficient_context"
                                ? "amber"
                                : "red"
                          }
                        >
                          {m.status === "ok"
                            ? "Grounded"
                            : m.status === "insufficient_context"
                              ? "Insufficient context"
                              : "Error"}
                        </StatusPill>
                        {m.model_name && (
                          <span className="text-[11px] text-charcoal-500">
                            {m.model_provider}/{m.model_name}
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                  {m.role === "assistant" && m.citations.length > 0 && (
                    <div className="mt-1.5">
                      <CitationsRow citations={m.citations} />
                    </div>
                  )}
                </div>
              ))
            )}
            {sending && (
              <div className="self-start max-w-[80%]">
                <Skeleton className="h-16 w-[320px]" />
              </div>
            )}
            <div ref={bottomRef} />
          </div>
          <div className="border-t border-charcoal-100 p-4">
            {error && (
              <div className="mb-2 text-[12px] text-status-red">{error}</div>
            )}
            <div className="flex gap-2 items-end">
              <div className="flex-1">
                <Textarea
                  rows={2}
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                  placeholder={
                    hasNoReadyDocs
                      ? "Upload a document before asking a question…"
                      : "Ask a grounded question about this opportunity…"
                  }
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      send(content);
                    }
                  }}
                />
              </div>
              <Button
                onClick={() => send(content)}
                loading={sending}
                disabled={!content.trim()}
              >
                Send
              </Button>
            </div>
          </div>
        </CardBody>
      </Card>
    </div>
  );
}
