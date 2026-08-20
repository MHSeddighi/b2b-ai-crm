"""Structured JSON contracts for the agent's LLM steps (plans and blocks).

The agent talks to the LLM in strict JSON and validates the output against
pydantic models (which also emit JSON Schema), instead of ad-hoc regex
extraction. Parsing is strict: optional markdown code fences are stripped, then
``json.loads`` + model validation.
"""
from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field


def parse_json_text(text: str) -> Any:
    """Strictly parse LLM JSON output, tolerating an optional markdown fence."""
    t = (text or "").strip()
    if t.startswith("```"):
        lines = [ln for ln in t.splitlines() if not ln.strip().startswith("```")]
        t = "\n".join(lines).strip()
    if not t:
        raise ValueError("empty LLM output")
    return json.loads(t)


# ---------------------------------------------------------------------------
# Plan contract
# ---------------------------------------------------------------------------
class PlanItem(BaseModel):
    kind: str = "query"  # "query" | "reuse" (unknown kinds treated as query)
    resultId: str = ""
    sql: str = ""
    purpose: str = ""


class PlanStep(BaseModel):
    tool: str = ""
    input: dict[str, Any] = Field(default_factory=dict)


class Plan(BaseModel):
    # New tool-calling style (what the current planner prompt emits).
    intent: str = ""
    steps: list[PlanStep] = Field(default_factory=list)
    assumption: str = ""
    state: dict[str, Any] = Field(default_factory=dict)
    # Legacy single-action style (still accepted / tested).
    action: str = ""
    resultId: str = ""
    sql: str = ""
    purpose: str = ""
    items: list[PlanItem] = Field(default_factory=list)


def plan_steps(plan: Plan, max_queries: int) -> list[dict]:
    """Flatten the planner output into a list of execution steps.

    Each step is ``{"kind": "query"|"reuse", "sql"/"resultId", "purpose"}``.
    If ``steps`` is present it wins; otherwise fall back to the legacy
    ``action`` / ``items`` fields. New SQL queries are capped at ``max_queries``;
    ``reuse`` steps never count against the cap.
    """
    steps: list[dict] = []
    new_queries = 0

    def push_query(sql: str, purpose: str) -> None:
        nonlocal new_queries
        if sql and new_queries < max_queries:
            steps.append({"kind": "query", "sql": sql, "purpose": purpose})
            new_queries += 1

    def push_reuse(result_id: str, purpose: str) -> None:
        if result_id:
            steps.append({"kind": "reuse", "resultId": result_id, "purpose": purpose})

    if plan.steps:
        for s in plan.steps:
            tool = s.tool
            inp = s.input or {}
            if tool == "reuse":
                push_reuse(inp.get("resultId") or "", inp.get("purpose") or "")
            elif tool in ("query", "run_sql"):
                push_query(inp.get("query") or inp.get("sql") or "",
                           inp.get("purpose") or "")
        return steps

    if plan.action == "reuse":
        push_reuse(plan.resultId, plan.purpose)
    elif plan.action == "query":
        push_query(plan.sql, plan.purpose)
    else:
        for it in plan.items:
            if it.kind == "reuse":
                push_reuse(it.resultId, it.purpose)
            else:
                push_query(it.sql, it.purpose)
    return steps


def parse_plan(text: str) -> Plan:
    data = parse_json_text(text)
    # tolerate top-level "queries" alias
    if isinstance(data, dict) and "items" not in data and "queries" in data:
        data["items"] = data.pop("queries")
    return Plan.model_validate(data)


def normalize_plan_items(plan: Plan, max_new_queries: int) -> list[dict]:
    """Flatten plan items to dicts, capping the number of new SQL queries.

    Reuse items never count against the query cap.
    """
    out: list[dict] = []
    new_queries = 0
    for it in plan.items:
        if it.kind == "reuse":
            if it.resultId:
                out.append({"kind": "reuse", "resultId": it.resultId,
                            "sql": "", "purpose": it.purpose})
        elif it.sql and new_queries < max_new_queries:
            out.append({"kind": "query", "resultId": it.resultId,
                        "sql": it.sql, "purpose": it.purpose})
            new_queries += 1
    return out


# ---------------------------------------------------------------------------
# Blocks contract (validated downstream by backend.schemas.blocks.validate_blocks)
# ---------------------------------------------------------------------------
def parse_blocks_json(text: str) -> list[dict] | None:
    """Parse a blocks payload: an array or {\"blocks\": [...]}. None if not JSON."""
    try:
        data = parse_json_text(text)
    except Exception:  # noqa: BLE001 - not JSON at all
        return None
    if isinstance(data, dict):
        data = data.get("blocks", [])
    if isinstance(data, list):
        return [b for b in data if isinstance(b, dict)]
    return None
