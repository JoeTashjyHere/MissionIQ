"use client";

import { use, useCallback, useEffect, useRef, useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { apiRequest, ApiError } from "@/lib/api";
import type { ChatMessage, ChatThread } from "@/lib/types";
import { PageHeader } from "@/components/PageHeader";
import { Card, CardBody, CardHeader } from "@/components/ds/Card";
import { Button } from "@/components/ds/Button";
import { Textarea } from "@/components/ds/Input";
import { StatusPill } from "@/components/ds/StatusPill";
import { CitationsRow } from "@/components/ds/Citation";

const STARTERS = [
  "Summarize the major requirements.",
  "What are the key evaluation drivers?",
  "Where are our biggest capability gaps?",
  "What capture questions are still unanswered?",
];

export default function AssistantPage({
  params,
}: {
  params: Promise<{ opportunityId: string }>;
}) {
  const { opportunityId } = use(params);
  const { currentWorkspaceId } = useAuth();
  const [thread, setThread] = useState<ChatThread | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
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
      const msgs = await apiRequest<ChatMessage[]>(`/chat/threads/${t.id}/messages`);
      setMessages(msgs);
    })().catch((e) => setError(e instanceof ApiError ? e.detail : "Failed to load chat."));
  }, [ensureThread]);

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
      setMessages((m) => [...m, resp.user_message, resp.assistant_message]);
      setContent("");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Send failed.");
    } finally {
      setSending(false);
    }
  };

  return (
    <div>
      <PageHeader
        eyebrow="Capture Intelligence"
        title="Intelligence Assistant"
        subtitle="Ask grounded questions about this opportunity. Citations required."
      />
      <Card>
        <CardHeader
          title="Conversation"
          subtitle={thread ? `Thread · ${thread.id.slice(0, 8)}` : "Initializing…"}
        />
        <CardBody className="!p-0">
          <div className="px-6 py-4 max-h-[60vh] min-h-[40vh] overflow-y-auto flex flex-col gap-4">
            {messages.length === 0 && (
              <div className="text-charcoal-500 text-[14px]">
                <p className="mb-3">Start with a question, or try one of these:</p>
                <div className="flex flex-col gap-1.5">
                  {STARTERS.map((s) => (
                    <button
                      key={s}
                      className="text-left text-[13px] text-steel-700 hover:underline"
                      onClick={() => send(s)}
                    >
                      → {s}
                    </button>
                  ))}
                </div>
              </div>
            )}
            {messages.map((m) => (
              <div
                key={m.id}
                className={`max-w-[80%] ${m.role === "user" ? "self-end" : "self-start"}`}
              >
                <div
                  className={`rounded-md px-4 py-3 text-[14px] ${
                    m.role === "user"
                      ? "bg-navy-900 text-white"
                      : "bg-white border border-charcoal-300 text-charcoal-900"
                  }`}
                >
                  <div className="whitespace-pre-wrap">{m.content}</div>
                  {m.role === "assistant" && (
                    <div className="mt-2 flex items-center gap-2">
                      <StatusPill
                        tone={
                          m.status === "ok"
                            ? "green"
                            : m.status === "insufficient_context"
                              ? "amber"
                              : "red"
                        }
                      >
                        {m.status}
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
            ))}
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
                  placeholder="Ask a grounded question about this opportunity…"
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      send(content);
                    }
                  }}
                />
              </div>
              <Button onClick={() => send(content)} loading={sending}>
                Send
              </Button>
            </div>
          </div>
        </CardBody>
      </Card>
    </div>
  );
}
