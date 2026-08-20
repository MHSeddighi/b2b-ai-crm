import type { AssistantResponse, Block, SqlResult } from "@/lib/blocks";
import { validateBlocks } from "@/lib/blocks";

export interface ChatResult {
  blocks: Block[];
  results: Record<string, SqlResult>;
  text?: string; // legacy fallback
}

// Backend is reached directly at its absolute path (no Vite proxy).
const BACKEND_PORT = Number(import.meta.env.VITE_BACKEND_PORT || 8000);
const API_URL = `http://127.0.0.1:${BACKEND_PORT}/api`;

export interface ChatHistoryItem {
  role: "user" | "assistant";
  content: string;
}

/** Send a question to the backend; returns the validated ordered block response. */
export async function fetchCopilotAnswer(
  question: string,
  history: ChatHistoryItem[] = [],
  sessionId?: string
): Promise<ChatResult> {
  const res = await fetch(`${API_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, history, session_id: sessionId }),
  });
  if (!res.ok) {
    throw new Error(`Backend returned ${res.status}`);
  }
  const data = (await res.json()) as Partial<ChatResult> & { results?: Record<string, unknown> };
  const blocks = validateBlocks(data.blocks);
  // Coerce results into typed SqlResult objects.
  const results: Record<string, SqlResult> = {};
  if (data.results) {
    for (const [k, v] of Object.entries(data.results)) {
      const r = v as SqlResult;
      results[k] = {
        resultId: r.resultId ?? k,
        columns: Array.isArray(r.columns) ? r.columns : [],
        rows: Array.isArray(r.rows) ? r.rows : [],
        n_rows: typeof r.n_rows === "number" ? r.n_rows : r.rows?.length ?? 0,
      };
    }
  }
  // If the backend returned a legacy single markdown-ish text, wrap it.
  if (!blocks.length && data.text) {
    return {
      blocks: validateBlocks([{ id: "b0", type: "markdown", content: data.text }]),
      results,
    };
  }
  return { blocks, results };
}

/** Build an AssistantResponse from a ChatResult (for mock fallback compatibility). */
export function toAssistantResponse(result: ChatResult): AssistantResponse {
  return { blocks: result.blocks, results: result.results };
}

// ---------------------------------------------------------------------------
// Streaming (SSE)
// ---------------------------------------------------------------------------

/** Events emitted by the /api/chat/stream SSE endpoint. */
export type StreamEvent =
  | { type: "status"; status: string }
  | { type: "thinking"; text: string }
  | { type: "text"; text: string }
  | {
      type: "blocks";
      blocks: Block[];
      results: Record<string, SqlResult>;
      query?: string;
    }
  | { type: "error"; message: string }
  | { type: "done" };

/** Hard cap on a single request so the loading state can never hang forever. */
const STREAM_TIMEOUT_MS = 240_000;

/**
 * Post a question to the streaming endpoint and yield parsed events as they
 * arrive. Throws if the backend is unreachable or the overall timeout expires
 * (the caller retries the connection on failure).
 */
export async function* fetchCopilotAnswerStream(
  question: string,
  history: ChatHistoryItem[] = [],
  sessionId?: string,
  signal?: AbortSignal
): AsyncGenerator<StreamEvent> {
  const controller = new AbortController();
  const onOuterAbort = () => controller.abort();
  signal?.addEventListener("abort", onOuterAbort, { once: true });
  const hardTimeout = setTimeout(() => controller.abort(), STREAM_TIMEOUT_MS);

  try {
    const res = await fetch(`${API_URL}/chat/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, history, session_id: sessionId }),
      signal: controller.signal,
    });

    if (!res.ok || !res.body) {
      throw new Error(`Backend returned ${res.status}`);
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      let idx: number;
      while ((idx = buffer.indexOf("\n\n")) !== -1) {
        const chunk = buffer.slice(0, idx);
        buffer = buffer.slice(idx + 2);
        const line = chunk.split("\n").find((l) => l.startsWith("data:"));
        if (!line) continue;
        const data = line.slice(5).trim();
        if (!data) continue;
        try {
          yield JSON.parse(data) as StreamEvent;
        } catch {
          // ignore malformed keep-alive frames
        }
      }
    }
  } finally {
    clearTimeout(hardTimeout);
    signal?.removeEventListener("abort", onOuterAbort);
  }
}
