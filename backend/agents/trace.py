"""Agent execution trace — observability for LLM calls, tool calls and stages.

Every interesting step of an answer (planner LLM call, plan, SQL/CRM tool
calls with their inputs+results, stored results, session state) is recorded as
a structured event. The streaming endpoint emits each event as an SSE frame as
it happens; the non-streaming endpoint returns the whole trace when
``debug=True``. Raw LLM payloads are only kept in debug mode, and every payload
is truncated so traces never blow up the wire.
"""
from __future__ import annotations

import json
import time
from typing import Any

# Per-payload char budget for tool results / raw LLM output.
_MAX_RAW_CHARS = 4000
_MAX_RESULT_CHARS = 3000


def _truncate(obj: Any, budget: int) -> Any:
    """Truncate a nested JSON-serializable object to a char budget."""
    try:
        s = json.dumps(obj, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        s = str(obj)
    if len(s) <= budget:
        return obj
    # Keep the structure, but cut the string representation with a marker.
    cut = s[:budget] + "\n…(truncated)"
    try:
        return json.loads(cut)
    except Exception:  # noqa: BLE001 - fall back to the cut string
        return cut


class Trace:
    """Collects ordered trace events; supports incremental drain for SSE."""

    def __init__(self, debug: bool = False) -> None:
        self.debug = debug
        self.events: list[dict[str, Any]] = []
        self._drained = 0

    # ------------------------------------------------------------------ record
    def _add(self, t: str, payload: dict[str, Any]) -> dict[str, Any]:
        ev = {"t": t, "ts": round(time.time(), 3), **payload}
        self.events.append(ev)
        return ev

    def meta(self, **kwargs: Any) -> dict[str, Any]:
        return self._add("meta", kwargs)

    def stage(self, stage: str, label: str = "", detail: str = "") -> dict[str, Any]:
        return self._add("stage", {"stage": stage, "label": label, "detail": detail})

    def llm(self, call: str, model: str, input_chars: int, output_chars: int,
            latency_ms: int, raw: str | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "call": call, "model": model, "input_chars": input_chars,
            "output_chars": output_chars, "latency_ms": latency_ms,
        }
        if self.debug and raw is not None:
            payload["raw"] = raw[:_MAX_RAW_CHARS]
        return self._add("llm", payload)

    def plan(self, intent: str, steps: list[dict], assumption: str) -> dict[str, Any]:
        return self._add("plan", {"intent": intent, "steps": steps,
                                  "assumption": assumption})

    def tool(self, tool: str, input: dict[str, Any], result: Any,
             latency_ms: int, ok: bool = True, error: str = "") -> dict[str, Any]:
        payload: dict[str, Any] = {
            "tool": tool, "input": _truncate(input, 800),
            "latency_ms": latency_ms, "ok": ok,
            "result": _truncate(result, _MAX_RESULT_CHARS),
        }
        if error:
            payload["error"] = error
        return self._add("tool", payload)

    def result(self, result_id: str, purpose: str, columns: list[str],
               n_rows: int) -> dict[str, Any]:
        return self._add("result", {"resultId": result_id, "purpose": purpose,
                                    "columns": columns, "n_rows": n_rows})

    def state(self, state: dict[str, Any]) -> dict[str, Any]:
        return self._add("state", {"state": state})

    # ------------------------------------------------------------------- read
    def drain(self) -> list[dict[str, Any]]:
        """Events recorded since the last drain (for incremental SSE emits)."""
        out = self.events[self._drained:]
        self._drained = len(self.events)
        return out

    def dump(self) -> list[dict[str, Any]]:
        return list(self.events)
