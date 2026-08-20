import { useMemo, useState } from "react";
import {
  Bug,
  Loader2,
  Maximize2,
  Minimize2,
  Plus,
  Send,
  Sparkles,
  Square,
  X,
} from "lucide-react";
import {
  AssistantRuntimeProvider,
  ComposerPrimitive,
  MessagePrimitive,
  ThreadPrimitive,
  useAuiState,
  useLocalRuntime,
  type DataMessagePartProps,
  type EmptyMessagePartProps,
  type ReasoningMessagePartProps,
  type TextMessagePartProps,
} from "@assistant-ui/react";
import ReactMarkdown from "react-markdown";

import { Button } from "@/components/ui/button";
import { BlockRenderer } from "@/components/block-renderer";
import { createCustomer360Adapter } from "@/lib/assistant-adapter";
import type { TraceEvent } from "@/lib/chat-api";
import type { Block, SqlResult } from "@/lib/blocks";

const SUGGESTED_QUESTIONS = [
  "چند مشتری فعال داریم؟",
  "برترین مشتریان از نظر درآمد کدامند؟",
  "روند فروش ماهانه را نشان بده",
  "پرتکرارترین دلایل شکایت چیست؟",
];

function AgentAvatar() {
  return (
    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-violet-500 text-white">
      <Sparkles className="h-4 w-4" />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Message part renderers
// ---------------------------------------------------------------------------
function TextPart({ text }: TextMessagePartProps) {
  return (
    <div className="prose-sm max-w-none text-sm leading-relaxed [&_table]:text-xs [&_table]:border [&_td]:border [&_th]:border [&_td]:px-2 [&_th]:px-2 [&_td]:py-1 [&_th]:py-1 [&_code]:rounded [&_code]:bg-muted [&_code]:px-1">
      <ReactMarkdown>{text}</ReactMarkdown>
    </div>
  );
}

function ChartSkeleton() {
  const bars = [45, 70, 30, 85, 55, 75, 40, 60];
  return (
    <div className="w-full rounded-xl border bg-card p-3">
      <div className="mb-3 h-3 w-32 animate-pulse rounded bg-muted" />
      <div dir="ltr" className="flex h-40 items-end gap-2 px-2">
        {bars.map((h, i) => (
          <div
            key={i}
            className="flex-1 animate-pulse rounded-t bg-muted/70"
            style={{ height: `${h}%`, animationDelay: `${i * 90}ms` }}
          />
        ))}
      </div>
    </div>
  );
}

function ReasoningPart({ text, status }: ReasoningMessagePartProps) {
  if (!text) return null;
  const running = status?.type === "running";
  if (!running) return null; // thinking collapses once the answer completes
  // A "preparing chart" note renders a chart skeleton so the user knows a
  // visual is about to appear exactly there.
  if (/نمودار/.test(text)) {
    return <ChartSkeleton />;
  }
  return (
    <div className="flex items-start gap-1.5 rounded-xl bg-muted/60 px-2.5 py-1.5 text-[11px] leading-relaxed text-muted-foreground">
      <Loader2 className="mt-0.5 h-3 w-3 shrink-0 animate-spin" />
      <span className="line-clamp-2 whitespace-pre-wrap break-words">{text}</span>
    </div>
  );
}

function EmptyPart(_props: EmptyMessagePartProps) {
  // The immediate "در حال تحلیل سؤال و جستجو در داده‌ها…" reasoning part is the
  // single loading indicator; this fallback deliberately renders nothing so a
  // second "در حال تحلیل…" line never appears alongside it.
  return null;
}

function BlocksPart({ data }: DataMessagePartProps<{ blocks: Block[]; results: Record<string, SqlResult> }>) {
  const { blocks, results } = data ?? { blocks: [], results: {} };
  if (!blocks?.length) return null;
  return (
    <div className="space-y-3">
      {blocks.map((block: Block) => (
        <BlockRenderer key={block.id} block={block} results={results ?? {}} />
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Debug trace panel — shows how the agent built the answer (LLM calls, plan,
// tool calls, results, state) as they happened.
// ---------------------------------------------------------------------------
const TRACE_BADGE: Record<string, string> = {
  meta: "bg-slate-500/15 text-slate-600",
  stage: "bg-indigo-500/15 text-indigo-600",
  llm: "bg-violet-500/15 text-violet-600",
  plan: "bg-amber-500/15 text-amber-600",
  tool: "bg-emerald-500/15 text-emerald-600",
  result: "bg-sky-500/15 text-sky-600",
  state: "bg-rose-500/15 text-rose-600",
};

function oneLine(ev: TraceEvent): string {
  switch (ev.type) {
    case "meta":
      return `session ${ev.session_id ?? "-"}`;
    case "stage":
      return `${ev.label || ev.stage}${ev.detail ? " · " + ev.detail : ""}`;
    case "llm":
      return `${ev.call} · ${ev.latency_ms}ms · ${ev.input_chars}→${ev.output_chars} chars`;
    case "plan":
      return `${ev.intent} · ${ev.steps?.length ?? 0} step(s)`;
    case "tool":
      return `${ev.tool} · ${ev.latency_ms}ms · ${ev.ok ? "ok" : "FAILED"}`;
    case "result":
      return `${ev.resultId} · ${ev.purpose || "-"} · ${ev.n_rows} rows`;
    case "state":
      return JSON.stringify(ev.state ?? {}).slice(0, 140);
    default:
      return "";
  }
}

function TraceRow({ ev }: { ev: TraceEvent }) {
  return (
    <details className="rounded-md border border-border/60 bg-background/60 px-2 py-1">
      <summary className="flex items-center gap-2 text-[11px] text-foreground/80">
        <span
          className={`rounded px-1.5 py-0.5 font-semibold uppercase ${TRACE_BADGE[ev.type] ?? "bg-muted text-muted-foreground"}`}
        >
          {ev.type}
        </span>
        <span className="truncate font-mono">{oneLine(ev)}</span>
      </summary>
      <pre className="mt-1.5 max-h-48 overflow-auto rounded bg-muted/60 p-2 text-[10px] leading-snug text-foreground/70">
        {JSON.stringify(ev, null, 2)}
      </pre>
    </details>
  );
}

function TracePart({ data }: DataMessagePartProps<{ events: TraceEvent[] }>) {
  const events = data?.events ?? [];
  if (!events.length) return null;
  return (
    <details className="rounded-xl border bg-muted/40 px-3 py-2">
      <summary className="flex cursor-pointer items-center gap-1.5 text-[11px] font-medium text-muted-foreground">
        <Bug className="h-3.5 w-3.5" />
        جزئیات فنی — مراحل ساخت پاسخ ({events.length} رویداد)
      </summary>
      <div dir="ltr" className="mt-2 max-h-72 space-y-1 overflow-y-auto">
        {events.map((ev: TraceEvent, i: number) => (
          <TraceRow key={i} ev={ev} />
        ))}
      </div>
    </details>
  );
}

// ---------------------------------------------------------------------------
// Messages
// ---------------------------------------------------------------------------
function UserMessage() {
  return (
    <MessagePrimitive.Root className="flex justify-end">
      <div className="max-w-[85%] rounded-2xl rounded-tr-sm bg-primary px-4 py-2.5 text-sm leading-relaxed text-primary-foreground">
        <MessagePrimitive.Parts
          components={{ Text: ({ text }: TextMessagePartProps) => <>{text}</> }}
        />
      </div>
    </MessagePrimitive.Root>
  );
}

function AssistantMessage() {
  return (
    <MessagePrimitive.Root className="flex gap-2.5">
      <AgentAvatar />
      <div className="min-w-0 flex-1 space-y-2.5">
        <MessagePrimitive.Parts
          components={{
            Empty: EmptyPart,
            Text: TextPart,
            Reasoning: ReasoningPart,
            data: { by_name: { blocks: BlocksPart, trace: TracePart } },
          }}
        />
      </div>
    </MessagePrimitive.Root>
  );
}

// ---------------------------------------------------------------------------
// Composer
// ---------------------------------------------------------------------------
function Composer({ onSuggest }: { onSuggest: (q: string) => void }) {
  const isRunning = useAuiState((s) => s.thread.isRunning);
  return (
    <ComposerPrimitive.Root className="shrink-0 space-y-2.5 border-t bg-card/60 p-3 backdrop-blur">
      <div className="flex flex-wrap gap-2">
        {SUGGESTED_QUESTIONS.map((q) => (
          <button
            key={q}
            type="button"
            disabled={isRunning}
            onClick={() => onSuggest(q)}
            className="rounded-full border bg-background px-3.5 py-1.5 text-xs text-muted-foreground transition-colors hover:border-primary/50 hover:text-foreground disabled:opacity-50"
          >
            {q}
          </button>
        ))}
      </div>

      <div className="flex items-end gap-2">
        <ComposerPrimitive.Input
          rows={1}
          autoFocus
          disabled={isRunning}
          placeholder="درباره مشتریان، ریسک، شکایات بپرسید..."
          className="flex-1 resize-none rounded-2xl border border-input bg-background px-4 py-3 text-sm leading-6 shadow-sm outline-none ring-offset-background placeholder:text-muted-foreground focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-60"
        />

        {/* ONE button in this spot: send when idle, stop while running. */}
        {isRunning ? (
          <ComposerPrimitive.Cancel asChild>
            <Button
              size="icon"
              variant="outline"
              aria-label="توقف تولید پاسخ"
              title="توقف تولید پاسخ"
              className="h-12 w-12 shrink-0 rounded-2xl border-red-500 text-red-500 hover:bg-red-50 hover:text-red-600"
            >
              <Square className="h-[18px] w-[18px] fill-current" />
            </Button>
          </ComposerPrimitive.Cancel>
        ) : (
          <ComposerPrimitive.Send asChild>
            <Button
              size="icon"
              aria-label="ارسال پیام"
              title="ارسال پیام"
              className="h-12 w-12 shrink-0 rounded-2xl"
            >
              <Send className="h-5 w-5" />
            </Button>
          </ComposerPrimitive.Send>
        )}
      </div>
    </ComposerPrimitive.Root>
  );
}

// ---------------------------------------------------------------------------
// Copilot
// ---------------------------------------------------------------------------
export type CopilotMode = "float" | "dock";

export interface CopilotProps {
  onClose: () => void;
  mode?: CopilotMode;
  onToggleMode?: () => void;
  /** Stable backend session id; changing it starts a fresh chat thread. */
  sessionId: string;
  onNewChat?: () => void;
}

export function Copilot({
  onClose,
  mode = "float",
  onToggleMode,
  sessionId,
  onNewChat,
}: CopilotProps) {
  const [debug, setDebug] = useState(false);
  const adapter = useMemo(
    () => createCustomer360Adapter(sessionId, debug),
    [sessionId, debug],
  );
  const runtime = useLocalRuntime(adapter, {
    initialMessages: [
      {
        role: "assistant",
        content:
          "سلام! من دستیار هوشمند بینش مشتری شما هستم. درباره مشتریان، فروش، ریسک، شکایات، کیفیت یا هر موضوع دیگری بپرسید.",
      },
    ],
  });

  return (
    <AssistantRuntimeProvider runtime={runtime}>
      <ThreadPrimitive.Root className="flex h-full flex-col bg-card">
        <div className="flex h-14 shrink-0 items-center gap-2 border-b px-4">
          <AgentAvatar />
          <div className="flex min-w-0 flex-col leading-tight">
            <span className="text-sm font-semibold">دستیار هوشمند</span>
            <span className="inline-flex items-center gap-1 text-[11px] text-emerald-500">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
              متصل · پایگاه‌داده واقعی
            </span>
          </div>
          <div className="mr-auto flex items-center gap-1">
            <Button
              variant={debug ? "default" : "ghost"}
              size="sm"
              onClick={() => setDebug((d) => !d)}
              aria-label="نمایش جزئیات فنی (مراحل ساخت پاسخ)"
              title="نمایش جزئیات فنی — مراحل، فراخوانی‌های مدل و ابزارها"
              className="h-9 gap-1.5 rounded-xl px-2.5 text-xs"
            >
              <Bug className="h-4 w-4" />
              {debug ? "جزئیات فنی: روشن" : "جزئیات فنی"}
            </Button>
            {onNewChat && (
              <Button
                variant="ghost"
                size="icon"
                onClick={onNewChat}
                aria-label="شروع گفتگوی جدید"
                title="شروع گفتگوی جدید"
                className="h-9 w-9 rounded-xl"
              >
                <Plus className="h-[18px] w-[18px]" />
              </Button>
            )}
            {onToggleMode && (
              <Button
                variant="ghost"
                size="icon"
                onClick={onToggleMode}
                aria-label={mode === "dock" ? "شناور کردن دستیار" : "باز کردن دستیار"}
                title={mode === "dock" ? "شناور کردن دستیار" : "باز کردن دستیار"}
                className="h-9 w-9 rounded-xl"
              >
                {mode === "dock" ? (
                  <Minimize2 className="h-[18px] w-[18px]" />
                ) : (
                  <Maximize2 className="h-[18px] w-[18px]" />
                )}
              </Button>
            )}
            <Button
              variant="ghost"
              size="icon"
              onClick={onClose}
              aria-label="بستن دستیار"
              className="h-9 w-9 rounded-xl"
            >
              <X className="h-[18px] w-[18px]" />
            </Button>
          </div>
        </div>

        <ThreadPrimitive.Viewport className="scrollbar-thin min-h-0 flex-1 overflow-y-auto px-4 py-4">
          <div className="flex flex-col gap-4">
            <ThreadPrimitive.Messages
              components={{ UserMessage, AssistantMessage }}
            />
          </div>
        </ThreadPrimitive.Viewport>

        <Composer onSuggest={(q) => runtime.thread.append(q)} />
      </ThreadPrimitive.Root>
    </AssistantRuntimeProvider>
  );
}
