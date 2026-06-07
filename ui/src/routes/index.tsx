import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import { MessageBubble } from "@/components/chat/MessageBubble";
import { InputArea } from "@/components/chat/InputArea";
import { StatusBar } from "@/components/chat/StatusBar";
import { useAppStore, type Message, type TaskEvent } from "@/lib/store";
import { api } from "@/lib/api";
import { Trash2, MessageSquarePlus } from "lucide-react";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Chat · Agent Black" },
      { name: "description", content: "Conversational research interface across CV, NLP, and ML agents." },
    ],
  }),
  component: ChatPage,
});

/** Strip trailing JSON objects/arrays/code-fences from a text string */
function extractTextOnly(text: string): string {
  if (!text) return "";
  let t = text.trim();
  if (isJsonLike(t)) return "";
  const patterns = [/\n\s*\{[\s\S]*$/, /\n\s*\[[\s\S]*$/, /```json[\s\S]*$/];
  for (const p of patterns) {
    const m = t.search(p);
    if (m > 0) t = t.substring(0, m).trim();
  }
  return t || text.trim();
}
function isJsonLike(s: string): boolean {
  const t = s.trim();
  return (t.startsWith("{") && t.endsWith("}")) || (t.startsWith("[") && t.endsWith("]"));
}

function ChatPage() {
  const messages = useAppStore((s) => s.messages);
  const addMessage = useAppStore((s) => s.addMessage);
  const updateMessage = useAppStore((s) => s.updateMessage);
  const replaceAllMessages = useAppStore((s) => s.replaceAllMessages);
  const clearMessages = useAppStore((s) => s.clearMessages);
  const endRef = useRef<HTMLDivElement>(null);
  const [sending, setSending] = useState(false);

  useEffect(() => {
    api.queryHistory().then((history) => {
      const toStr = (v: any): string | null => {
        if (v == null) return null;
        if (typeof v === "string") return v;
        try { return JSON.stringify(v, null, 2); } catch { return String(v); }
      };
        const synced = history.flatMap((h) => {
        const userMsg: Message = {
          id: `hist-user-${h.id}`,
          role: "user",
          content: h.query,
          timestamp: h.created_at * 1000,
        };
        const sections = {
          literature_review: toStr(h.report?.literature_review),
          datasets: toStr(h.report?.datasets),
          models: toStr(h.report?.models),
          evaluation_plan: toStr(h.report?.evaluation_plan),
          prototype_guidance: toStr(h.report?.prototype_guidance),
        };
        const assistantMsg: Message = {
          id: `hist-asst-${h.id}`,
          role: "assistant",
          content: toStr(h.report?.content) || extractTextOnly(sections.literature_review || "") || "Research complete.",
          timestamp: h.created_at * 1000,
          sections,
          agentsUsed: h.agents_used,
          raw: { ...h.report, diagram: h.diagram },
        };
        return [userMsg, assistantMsg];
      });
      replaceAllMessages(synced);
    }).catch(() => {});
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length]);

  const handleClearChat = async () => {
    clearMessages();
    try { await api.clearHistory(); } catch {}
  };

  const handleNewChat = () => {
    clearMessages();
  };

  const handleSubmit = async (text: string) => {
    if (sending) return;
    setSending(true);
    const userMsg: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: text,
      timestamp: Date.now(),
    };
    const placeholderId = crypto.randomUUID();
    const placeholder: Message = {
      id: placeholderId,
      role: "assistant",
      content: "",
      timestamp: Date.now(),
      pending: true,
      taskProgress: [],
    };
    addMessage(userMsg);
    addMessage(placeholder);

    try {
      const { task_id } = await api.submitQuery(text);

      api.streamTask(
        task_id,
        (ev: TaskEvent) => {
          const current = useAppStore.getState().messages.find(m => m.id === placeholderId)?.taskProgress || [];
          const merged = [...current.filter((e) => e.step !== ev.step), ev];
          updateMessage(placeholderId, { taskProgress: merged });
        },
        (result) => {
          const toStr = (v: any): string | null => {
            if (v == null) return null;
            if (typeof v === "string") return v;
            try { return JSON.stringify(v, null, 2); } catch { return String(v); }
          };
          if (result.status === "error" || !result.report) {
            updateMessage(placeholderId, {
              pending: false,
              content: result.error ? `Error: ${result.error}` : "Query failed. Please check that the LLM provider and agents are configured correctly.",
              raw: result,
            });
          } else {
            const r = result.report;
            const sections = {
              literature_review: toStr(r?.literature_review),
              datasets: toStr(r?.datasets),
              models: toStr(r?.models),
              evaluation_plan: toStr(r?.evaluation_plan),
              prototype_guidance: toStr(r?.prototype_guidance),
            };
            const content = toStr(r?.content) || extractTextOnly(sections.literature_review || "") || "Research complete. See sections below.";
            updateMessage(placeholderId, {
              pending: false,
              content,
              sections,
              agentsUsed: result.agents_used?.length ? result.agents_used : undefined,
              raw: result,
            });
          }
        },
        (err) => {
          updateMessage(placeholderId, {
            pending: false,
            content: `Error: ${err.message}`,
          });
        },
      );
    } catch (err: any) {
      updateMessage(placeholderId, {
        pending: false,
        content: `Error: ${err.message}. Check that agents are running.`,
      });
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="flex flex-1 flex-col">
      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto flex w-full max-w-[860px] flex-col gap-6 px-3 py-4 sm:px-4 sm:py-6">
          <StatusBar />
          {messages.length === 0 ? (
            <EmptyState onPrompt={handleSubmit} />
          ) : (
            <>
              <div className="flex flex-wrap items-center justify-end gap-2">
                <button
                  onClick={handleNewChat}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-surface px-3 py-1.5 text-xs text-text-secondary hover:bg-surface-hover transition-colors"
                >
                  <MessageSquarePlus className="h-3.5 w-3.5" />
                  New Chat
                </button>
                <button
                  onClick={handleClearChat}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-surface px-3 py-1.5 text-xs text-text-secondary hover:bg-surface-hover hover:text-red-400 transition-colors"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                  Clear History
                </button>
              </div>
              <div className="flex flex-col gap-6">
                {messages.map((m) => (
                  <MessageBubble key={m.id} message={m} />
                ))}
              </div>
            </>
          )}
          <div ref={endRef} />
        </div>
      </div>
      <InputArea onSubmit={handleSubmit} disabled={sending} />
    </div>
  );
}

function EmptyState({ onPrompt }: { onPrompt: (text: string) => void }) {
  const samples = [
    "Build an OCR solution for handwritten receipts",
    "Compare modern speech recognition architectures",
    "Design a recommendation system for a niche e-commerce site",
    "Survey methods for few-shot image classification",
  ];
  return (
    <div className="mt-8 flex flex-col items-center text-center">
      <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-2xl border border-border bg-surface text-sm font-bold tracking-tighter">
        A·B
      </div>
      <h1 className="text-lg font-semibold tracking-tight sm:text-2xl">
        What should the agents research today?
      </h1>
      <p className="mt-2 max-w-md text-xs text-text-secondary sm:text-sm">
        The orchestrator routes your query to CV, NLP, and ML agents and returns a structured research brief.
      </p>
      <div className="mt-8 grid w-full gap-2 sm:grid-cols-2">
        {samples.map((s) => (
          <button
            key={s}
            onClick={() => onPrompt(s)}
            className="rounded-xl border border-border bg-surface/60 px-4 py-3 text-left text-sm text-foreground hover:bg-surface-hover transition-colors"
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}
