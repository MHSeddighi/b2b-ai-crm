"""Bounded conversation context for the copilot agent.

The goal is to keep the LLM context small and predictable as a conversation and
the database grow:

- **Exact MCP/database results** live in a per-session ``ResultStore`` keyed by
  the **server-generated** resultId. They are never copied into the
  conversation history or the analytical state.
- **History/state** keep only lightweight metadata: a compact summary of older
  turns, the last N recent messages, a small structured analytical state
  (selected customer/product/order, date range, filters, intent, active
  resultIds) and per-result metadata (resultId, purpose, columns, n_rows).
- ``build_context`` renders that bounded data into a small prompt payload. The
  LLM is shown at most a tiny row sample, never the full data grids.

This module is pure and unit-testable (no network/LLM).
"""
from __future__ import annotations

import json
from typing import Any, Iterable

from backend.schemas.blocks import SqlResult

# ---------------------------------------------------------------------------
# Bounds — everything below keeps context size bounded.
# ---------------------------------------------------------------------------
# Full messages kept verbatim in the recent window.
MAX_RECENT_MESSAGES = 6
# Compact older-turn summary entries kept (each is just {q, a}).
MAX_LOG_ENTRIES = 20
MAX_Q_CHARS = 200
MAX_A_CHARS = 260
MAX_MSG_CHARS = 400

# ResultStore cap (number of exact results held per session).
MAX_STORED_RESULTS = 25
# How many result metadata entries we expose to the LLM at once.
MAX_RESULT_META = 12
# Row sample shown to the LLM for reasoning (never the full grid). Comparison
# breakdowns (e.g. one row per category) are useless if truncated to a couple
# of rows — the model then falls back to whatever metric it can actually see.
MAX_SAMPLE_ROWS = 15
# How many active resultIds are kept in analytical state.
MAX_STATE_RESULT_IDS = 8

# Upper bound (in chars) for the whole rendered context prompt, so a long chat
# or huge DB results can never blow up the LLM input.
MAX_CONTEXT_CHARS = 6000


def _trunc(value: str, limit: int) -> str:
    value = str(value)
    return value if len(value) <= limit else value[:limit] + "…"


class SessionState:
    """Per-conversation state. Exact data is kept only in ``result_store``."""

    def __init__(self, session_id: str = "_") -> None:
        self.session_id = session_id
        # Compact summary of older turns: [{"q": "...", "a": "..."}]
        self.log: list[dict[str, str]] = []
        # Recent full messages (last MAX_RECENT_MESSAGES) as {role, content}.
        self.recent: list[dict[str, str]] = []
        # Structured analytical state (small JSON).
        self.state: dict[str, Any] = {}
        # Lightweight metadata: resultId -> {purpose, columns, n_rows}
        self.result_meta: dict[str, dict[str, Any]] = {}
        # EXACT results keyed by server-generated resultId (separate store).
        self.result_store: dict[str, SqlResult] = {}
        self._insertion: list[str] = []

    # ------------------------------------------------------------------ results
    def add_result(self, resultId: str, purpose: str,
                   columns: list[str], rows: list[list[Any]],
                   n_rows: int | None = None) -> SqlResult:
        """Store an exact result and its metadata. Bounded by MAX_STORED_RESULTS.

        ``n_rows`` (from the MCP server) is honoured when provided — the server
        may truncate rows while reporting the true total.
        """
        count = n_rows if n_rows is not None else len(rows)
        sr = SqlResult(resultId=resultId, columns=list(columns),
                       rows=rows, n_rows=count)
        self.result_store[resultId] = sr
        self.result_meta[resultId] = {
            "purpose": purpose,
            "columns": list(columns),
            "n_rows": count,
        }
        self._insertion.append(resultId)
        self._evict_results()
        return sr

    def _evict_results(self) -> None:
        """Drop the oldest results beyond MAX_STORED_RESULTS (FIFO)."""
        while len(self.result_store) > MAX_STORED_RESULTS and self._insertion:
            oldest = self._insertion.pop(0)
            # never evict something referenced by the active state's current turn
            self.result_store.pop(oldest, None)
            self.result_meta.pop(oldest, None)

    def get_result(self, resultId: str) -> SqlResult | None:
        return self.result_store.get(resultId)

    def result_meta_prompt(self, ids: Iterable[str]) -> str:
        """Metadata-only lines for the LLM (no rows). Bounded to MAX_RESULT_META."""
        lines = []
        for rid in list(ids)[:MAX_RESULT_META]:
            m = self.result_meta.get(rid)
            if not m:
                continue
            lines.append(
                f"- resultId={rid} | purpose={m['purpose']} | "
                f"columns={json.dumps(m['columns'], ensure_ascii=False)} | "
                f"n_rows={m['n_rows']}"
            )
        return "\n".join(lines)

    def result_samples(self, ids: Iterable[str], n: int = MAX_SAMPLE_ROWS) -> str:
        """Small row samples for the LLM (never more than ``n`` rows per result)."""
        lines = []
        for rid in list(ids)[:MAX_RESULT_META]:
            sr = self.result_store.get(rid)
            if not sr:
                continue
            sample = sr.rows[:n]
            lines.append(
                f"- resultId={rid} | columns={json.dumps(sr.columns, ensure_ascii=False)} | "
                f"n_rows={sr.n_rows}\n  sample={json.dumps(sample, ensure_ascii=False)[:2000]}"
            )
        return "\n".join(lines)

    # ------------------------------------------------------------------- turns
    def record_turn(self, question: str, answer_preview: str) -> None:
        """Append a compact turn summary + update the recent window (bounded)."""
        self.log.append({
            "q": _trunc(question, MAX_Q_CHARS),
            "a": _trunc(answer_preview, MAX_A_CHARS),
        })
        if len(self.log) > MAX_LOG_ENTRIES:
            self.log = self.log[-MAX_LOG_ENTRIES:]

        self.recent.append({"role": "user", "content": _trunc(question, MAX_MSG_CHARS)})
        self.recent.append({"role": "assistant", "content": _trunc(answer_preview, MAX_MSG_CHARS)})
        if len(self.recent) > MAX_RECENT_MESSAGES * 2:
            self.recent = self.recent[-(MAX_RECENT_MESSAGES * 2):]

    def seed_from_history(self, history: list[dict] | None) -> None:
        """Bound an externally-provided history into the recent window."""
        for m in (history or [])[-(MAX_RECENT_MESSAGES * 2):]:
            role = "assistant" if m.get("role") == "assistant" else "user"
            self.recent.append({
                "role": role,
                "content": _trunc(str(m.get("content", "")), MAX_MSG_CHARS),
            })
        self.recent = self.recent[-(MAX_RECENT_MESSAGES * 2):]

    # ------------------------------------------------------------------- state
    def update_state(self, patch: Any) -> None:
        if not isinstance(patch, dict):
            return
        for k, v in patch.items():
            if v is None or v == "":
                self.state.pop(k, None)
            else:
                self.state[k] = v
        ids = self.state.get("active_result_ids")
        if isinstance(ids, list):
            self.state["active_result_ids"] = ids[-MAX_STATE_RESULT_IDS:]

    def active_result_ids(self) -> list[str]:
        ids = self.state.get("active_result_ids") or []
        return [r for r in ids if r in self.result_store]

    # ------------------------------------------------------------------ render
    def context_parts(self, question: str,
                      active_ids: Iterable[str] | None = None) -> dict[str, str]:
        """Build the bounded context payload (no full rows) for this turn."""
        parts: dict[str, str] = {}
        if self.log:
            parts["summary"] = json.dumps(self.log, ensure_ascii=False)
        if self.recent:
            parts["recent"] = "\n".join(
                f"{m['role']}: {m['content']}" for m in self.recent)
        if self.state:
            parts["state"] = json.dumps(self.state, ensure_ascii=False)
        ids = list(active_ids) if active_ids is not None else self.active_result_ids()
        meta = self.result_meta_prompt(ids)
        if meta:
            parts["results"] = meta
        parts["question"] = question
        return parts

    def context_size(self, question: str) -> int:
        return len(self.render_context(question))

    def render_context(self, question: str,
                       active_ids: Iterable[str] | None = None) -> str:
        parts = self.context_parts(question, active_ids)
        out = [f"سؤال: {parts['question']}"]
        if "summary" in parts:
            out.append(f"خلاصه گفتگوهای قدیمی‌تر:\n{parts['summary']}")
        if "recent" in parts:
            out.append(f"پیام‌های اخیر:\n{parts['recent']}")
        if "state" in parts:
            out.append(f"وضعیت تحلیلی فعلی:\n{parts['state']}")
        if "results" in parts:
            out.append(f"نتایج موجود (فقط متادیتا):\n{parts['results']}")
        return "\n\n".join(out)[:MAX_CONTEXT_CHARS]


def _block_attr(b: Any, key: str, default: Any = "") -> Any:
    """Read a block field whether ``b`` is a validated model instance or a
    plain dict (e.g. from ``.model_dump()``) — ``getattr`` alone silently
    returns the default for every dict, since dicts don't expose keys as
    attributes."""
    if isinstance(b, dict):
        return b.get(key, default)
    return getattr(b, key, default)


def answer_preview(blocks: list[Any]) -> str:
    """A short preview of an assistant reply for the summary log (never full data)."""
    parts: list[str] = []
    for b in blocks[:4]:
        t = _block_attr(b, "type", "?")
        if t == "markdown":
            parts.append(_trunc(_block_attr(b, "content", ""), 160))
        elif t in ("metric",):
            parts.append(f"[metric:{_block_attr(b, 'label', '')}]")
        elif t == "chart":
            parts.append(f"[chart:{_block_attr(b, 'chartType', '')}]")
        elif t == "table":
            parts.append("[table]")
        elif t == "customer_card":
            parts.append(f"[customer:{_block_attr(b, 'customerId', '')}]")
        elif t == "product_card":
            parts.append(f"[product:{_block_attr(b, 'productId', '')}]")
        elif t == "order_card":
            parts.append(f"[order:{_block_attr(b, 'orderId', '')}]")
        elif t == "recommendation":
            parts.append("[recommendation]")
    return " | ".join(parts) or "(پاسخ)"