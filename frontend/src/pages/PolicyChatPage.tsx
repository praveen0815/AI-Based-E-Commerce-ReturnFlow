import { useCallback, useEffect, useRef, useState } from "react";

import { PageHeader } from "../components/PageHeader";
import { Alert } from "../components/ui/Alert";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Input } from "../components/ui/Input";
import { Spinner } from "../components/ui/Spinner";
import { useAuth } from "../hooks/useAuth";
import { ApiError } from "../services/api";
import { askPolicyQuestion, reindexKnowledge, submitPolicyFeedback } from "../services/rag";
import type { ChatMessage, RagCitation } from "../types/rag";
import { hasPermission } from "../utils/access";

const STORAGE_KEY = "returnflow-policy-chat";

function loadHistory(storeId: string): ChatMessage[] {
  try {
    const raw = sessionStorage.getItem(`${STORAGE_KEY}:${storeId}`);
    if (!raw) {
      return [];
    }
    return JSON.parse(raw) as ChatMessage[];
  } catch {
    return [];
  }
}

function saveHistory(storeId: string, messages: ChatMessage[]) {
  sessionStorage.setItem(`${STORAGE_KEY}:${storeId}`, JSON.stringify(messages.slice(-40)));
}

export function PolicyChatPage() {
  const { activeMembership, storeId } = useAuth();
  const canManage = hasPermission(activeMembership?.permissions, "knowledge:manage");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [reindexNote, setReindexNote] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!storeId) {
      return;
    }
    setMessages(loadHistory(storeId));
  }, [storeId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const persist = useCallback(
    (next: ChatMessage[]) => {
      setMessages(next);
      if (storeId) {
        saveHistory(storeId, next);
      }
    },
    [storeId],
  );

  async function onAsk(event: React.FormEvent) {
    event.preventDefault();
    const trimmed = question.trim();
    if (trimmed.length < 3 || loading) {
      return;
    }
    setLoading(true);
    setError("");
    const userMessage: ChatMessage = { id: crypto.randomUUID(), role: "user", content: trimmed };
    persist([...messages, userMessage]);
    setQuestion("");
    try {
      const response = await askPolicyQuestion(trimmed);
      const assistant: ChatMessage = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: response.answer,
        grounded: response.grounded,
        citations: response.citations,
        model: response.model,
      };
      persist([...messages, userMessage, assistant]);
    } catch (caught) {
      const message = caught instanceof ApiError ? caught.message : "The policy assistant is unavailable.";
      setError(message);
      persist([
        ...messages,
        userMessage,
        { id: crypto.randomUUID(), role: "assistant", content: message, error: true },
      ]);
    } finally {
      setLoading(false);
    }
  }

  async function onReindex() {
    setReindexNote("");
    setError("");
    try {
      const result = await reindexKnowledge();
      setReindexNote(`Indexed ${result.indexed} of ${result.total} documents.`);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Reindex failed.");
    }
  }

  async function onFeedback(helpful: boolean, userQuestion: string, answer: string) {
    try {
      await submitPolicyFeedback({
        helpful,
        question: userQuestion,
        answer_excerpt: answer.slice(0, 400),
      });
    } catch {
      /* non-blocking */
    }
  }

  function precedingUserText(index: number): string {
    for (let i = index - 1; i >= 0; i -= 1) {
      if (messages[i]?.role === "user") {
        return messages[i].content;
      }
    }
    return "";
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Policy AI"
        title="Policy assistant"
        description="Answers are grounded in indexed return-policy documents for the selected store. The model will not invent refund rules when evidence is missing."
        actions={
          canManage ? (
            <Button type="button" variant="secondary" onClick={() => void onReindex()}>
              Reindex knowledge
            </Button>
          ) : undefined
        }
      />
      {reindexNote ? (
        <Alert tone="info" title="Index updated">
          {reindexNote}
        </Alert>
      ) : null}
      {error ? (
        <Alert tone="danger" title="Error">
          {error}
        </Alert>
      ) : null}

      <Card className="flex h-[min(70vh,42rem)] flex-col overflow-hidden">
        <div className="flex-1 space-y-4 overflow-y-auto p-4">
          {messages.length === 0 ? (
            <p className="text-sm text-ink-muted">
              Ask about return windows, refund timing, or shipping rules. Upload documents in Knowledge, then reindex.
            </p>
          ) : null}
          {messages.map((message, index) => (
            <div
              key={message.id}
              className={`max-w-3xl rounded-2xl px-4 py-3 text-sm ${
                message.role === "user"
                  ? "ml-auto bg-cyan-400/15 text-cyan-50"
                  : "bg-navy-800 text-ink"
              } ${message.error ? "border border-rose-500/40" : ""}`}
            >
              <p className="whitespace-pre-wrap">{message.content}</p>
              {message.role === "assistant" && message.citations && message.citations.length > 0 ? (
                <div className="mt-3 space-y-2 border-t border-navy-600 pt-3">
                  <p className="text-xs font-semibold uppercase tracking-wide text-ink-faint">Sources</p>
                  {message.citations.map((cite: RagCitation) => (
                    <div key={`${cite.label}-${cite.chunk_index}`} className="rounded-lg bg-navy-950/80 p-2 text-xs text-ink-muted">
                      <p className="font-medium text-ink">
                        {cite.label}: {cite.original_filename ?? "Document"}
                        {cite.page_hint ? ` · ${cite.page_hint}` : ""}
                        {cite.section_label ? ` · ${cite.section_label}` : ""}
                      </p>
                      <p className="mt-1">Score {cite.score.toFixed(2)}</p>
                      <p className="mt-1 line-clamp-3">{cite.excerpt}</p>
                    </div>
                  ))}
                </div>
              ) : null}
              {message.role === "assistant" && !message.error ? (
                <div className="mt-3 flex gap-2">
                  <Button
                    type="button"
                    variant="secondary"
                    onClick={() => void onFeedback(true, precedingUserText(index), message.content)}
                  >
                    Helpful
                  </Button>
                  <Button
                    type="button"
                    variant="secondary"
                    onClick={() => void onFeedback(false, precedingUserText(index), message.content)}
                  >
                    Not helpful
                  </Button>
                </div>
              ) : null}
              {message.role === "assistant" && message.model ? (
                <p className="mt-2 text-xs text-ink-faint">Model: {message.model}</p>
              ) : null}
            </div>
          ))}
          {loading ? <Spinner label="Generating answer" /> : null}
          <div ref={bottomRef} />
        </div>

        <form className="border-t border-navy-600 p-4" onSubmit={onAsk}>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
            <Input
              id="policy-question"
              label="Question"
              className="flex-1"
              value={question}
              placeholder="e.g. How long do customers have to return an item?"
              onChange={(event) => setQuestion(event.target.value)}
              disabled={loading}
            />
            <Button type="submit" className="sm:mb-0.5" disabled={loading}>
              Ask
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}