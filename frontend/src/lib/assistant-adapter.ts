// assistant-ui ChatModelAdapter that bridges the Customer 360 SSE stream to
// assistant-ui message parts:
//   - "thinking" events  -> reasoning parts (streamed, collapsible)
//   - "text" events      -> text parts (streamed token-by-token)
//   - "blocks" events    -> a single data part named "blocks" carrying the
//                           structured blocks (charts/tables/cards) + results
//
// The message parts are ordered [reasoning, blocks, text] so charts and cards
// appear ABOVE the narrative explanation (blocks arrive last on the wire, but
// we render them before the text so the visual comes first).
import type {
  ChatModelAdapter,
  ChatModelRunResult,
  ThreadAssistantMessagePart,
  ThreadMessage,
} from "@assistant-ui/react";

import { fetchCopilotAnswerStream, type ChatHistoryItem, type TraceEvent } from "@/lib/chat-api";
import type { Block, SqlResult } from "@/lib/blocks";
import { fixPersianZwnj } from "@/lib/persian";

export const UNREACHABLE_MSG =
  "متأسفانه به سرور پشتیبان متصل نشدم. لطفاً مطمئن شوید سرور پشتیبان در حال اجراست و دوباره تلاش کنید.";

/** Shown when the backend WAS reached but the connection dropped mid-answer. */
export const CONNECTION_DROPPED_MSG =
  "ارتباط با سرور در حین پاسخ‌گویی قطع شد. لطفاً دوباره تلاش کنید.";

const STARTING_MSG = "در حال تحلیل سؤال و جستجو در داده‌ها…";

/** How many times to retry a failed CONNECTION before showing the error. */
const MAX_CONNECT_ATTEMPTS = 4;
/** Backoff between connection attempts (the backend may be reloading). */
const RETRY_DELAY_MS = 700;

function lastUserText(messages: readonly ThreadMessage[]): string {
  for (let i = messages.length - 1; i >= 0; i--) {
    const m = messages[i];
    if (m.role !== "user") continue;
    const text = m.content
      .filter((p) => p.type === "text")
      .map((p) => (p as { text: string }).text)
      .join("\n");
    if (text.trim()) return text;
  }
  return "";
}

function buildHistory(messages: readonly ThreadMessage[]): ChatHistoryItem[] {
  const out: ChatHistoryItem[] = [];
  for (const m of messages) {
    if (m.role === "user") {
      const text = m.content
        .filter((p) => p.type === "text")
        .map((p) => (p as { text: string }).text)
        .join("\n");
      if (text.trim()) out.push({ role: "user", content: text });
    } else if (m.role === "assistant") {
      const text = m.content
        .filter((p) => p.type === "text")
        .map((p) => (p as { text: string }).text)
        .join("\n");
      if (text.trim()) out.push({ role: "assistant", content: text });
    }
  }
  return out.slice(-12);
}

/**
 * Build the full accumulated content from streaming state.
 * Order: reasoning (thinking/status), trace (debug events), blocks (charts/cards), text (narrative).
 */
function buildContent(
  reasoning: string,
  narrative: string,
  blocks: Block[],
  results: Record<string, SqlResult>,
  trace: TraceEvent[],
  status: "running" | "complete",
): ThreadAssistantMessagePart[] {
  const parts: ThreadAssistantMessagePart[] = [];
  if (reasoning) {
    parts.push({ type: "reasoning", text: reasoning, status: { type: status } });
  }
  if (trace.length) {
    parts.push({
      type: "data",
      name: "trace",
      data: { events: trace },
    } as ThreadAssistantMessagePart);
  }
  if (blocks.length) {
    parts.push({
      type: "data",
      name: "blocks",
      data: { blocks, results },
    } as ThreadAssistantMessagePart);
  }
  if (narrative) {
    parts.push({ type: "text", text: fixPersianZwnj(narrative), status: { type: status } });
  }
  return parts;
}

export function createCustomer360Adapter(
  sessionId: string,
  debug = false,
): ChatModelAdapter {
  return {
    async *run({ messages, abortSignal }): AsyncGenerator<ChatModelRunResult, void> {
      const question = lastUserText(messages);
      const history = buildHistory(messages);

      let reasoning = "";
      let narrative = "";
      let blocks: Block[] = [];
      let results: Record<string, SqlResult> = {};
      const trace: TraceEvent[] = [];
      // Emit a real part immediately so the message never sits at an empty
      // loading state while the (potentially slow) planner produces its first
      // token.
      reasoning = STARTING_MSG;
      yield { content: buildContent(reasoning, narrative, blocks, results, trace, "running") };

      if (!question) {
        yield {
          content: [{ type: "text", text: "", status: { type: "complete" } }],
          status: { type: "complete", reason: "unknown" },
        };
        return;
      }

      // Tracks whether the request actually reached the backend (as opposed to
      // never connecting), so we can show the right message on a drop.
      let receivedAny = false;
      let postStreamDropRetried = false;
      try {
        // Reconnect-and-continue: retry whenever the connection fails before
        // any narrative text has rendered (backend mid-reload, a dropped
        // connection during the long planning/SQL phase). Once text starts
        // streaming we never retry, to avoid duplicating the answer.
        for (let attempt = 0; attempt < MAX_CONNECT_ATTEMPTS; attempt++) {
          try {
            for await (const ev of fetchCopilotAnswerStream(question, history, sessionId, abortSignal, debug)) {
              if (abortSignal.aborted) break;
              receivedAny = true;
              if (ev.type === "thinking") {
                // Real thinking replaces the placeholder loading note.
                reasoning =
                  reasoning === STARTING_MSG ? ev.text : reasoning + ev.text;
              } else if (ev.type === "text") {
                narrative += ev.text;
              } else if (ev.type === "blocks") {
                blocks = ev.blocks;
                results = ev.results;
                // The chart/cards have arrived — drop any "preparing chart"
                // loader so it never lingers once the visual is rendered.
                reasoning = "";
              } else if (ev.type === "error") {
                narrative = ev.message;
              } else if (
                ev.type === "meta" || ev.type === "stage" || ev.type === "llm" ||
                ev.type === "plan" || ev.type === "tool" || ev.type === "result" ||
                ev.type === "state"
              ) {
                trace.push(ev);
              }
              yield { content: buildContent(reasoning, narrative, blocks, results, trace, "running") };
            }
            break; // stream completed cleanly
          } catch (err) {
            const aborted =
              abortSignal.aborted ||
              (err instanceof DOMException && err.name === "AbortError");
            // A drop after some events but before any text is allowed one
            // reconnect; connection-refused before any event is retried as
            // before. Never retry once narrative text has started.
            const retriedDrop = receivedAny && !narrative && !postStreamDropRetried;
            if (aborted || narrative || attempt === MAX_CONNECT_ATTEMPTS - 1) throw err;
            if (retriedDrop) postStreamDropRetried = true;
            await new Promise((r) => setTimeout(r, RETRY_DELAY_MS * (attempt + 1)));
          }
        }
      } catch (err) {
        // Aborts are expected (user pressed stop) — finish silently.
        if (!(err instanceof DOMException && err.name === "AbortError")) {
          if (!narrative) {
            narrative = receivedAny ? CONNECTION_DROPPED_MSG : UNREACHABLE_MSG;
          }
        }
      }

      yield {
        content: buildContent(reasoning, narrative, blocks, results, trace, "complete"),
        status: { type: "complete", reason: "unknown" },
      };
    },
  };
}
