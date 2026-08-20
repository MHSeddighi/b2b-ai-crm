#!/usr/bin/env python3
"""Debug the Customer 360 agent: show every LLM call, plan, tool call and
result that produced an answer — no guessing.

Usage:
    python scripts/debug_agent.py "what should we do with customer C_317124?"
    python scripts/debug_agent.py --no-raw "برترین مشتریان از نظر درآمد کدامند؟"

Options:
    --no-raw   do not print raw LLM JSON (keeps output compact)
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys

sys.path.insert(0, ".")

from backend.agents import db_agent  # noqa: E402

_LABELS = {
    "meta": "META",
    "stage": "STAGE",
    "llm": "LLM",
    "plan": "PLAN",
    "tool": "TOOL",
    "result": "RESULT",
    "state": "STATE",
}


def _fmt(v: object, budget: int = 600) -> str:
    try:
        s = json.dumps(v, ensure_ascii=False, default=str, indent=2)
    except (TypeError, ValueError):
        s = str(v)
    return s if len(s) <= budget else s[:budget] + "\n…(truncated)"


def _render(events: list[dict], raw: bool) -> str:
    out: list[str] = []
    for ev in events:
        t = ev.get("t", "?")
        tag = _LABELS.get(t, t.upper())
        out.append(f"\n── {tag} ───────────────────────────────────────────")
        for k, v in ev.items():
            if k in ("t", "ts"):
                continue
            if k == "raw" and not raw:
                continue
            out.append(f"{k}: {_fmt(v)}")
    return "\n".join(out)


async def main(question: str, raw: bool) -> int:
    print(f"QUESTION: {question}\n")
    try:
        result = await db_agent.answer(question, session_id="debug", debug=True)
    finally:
        await db_agent.close_mcp()

    blocks = result.get("blocks", [])
    trace = result.get("trace", [])

    print("=" * 60)
    print("AGENT TRACE")
    print("=" * 60)
    print(_render(trace, raw))

    print("\n" + "=" * 60)
    print(f"ANSWER ({len(blocks)} blocks)")
    print("=" * 60)
    for b in blocks:
        if b.type == "markdown":
            print("\n" + b.content)
        else:
            print(f"\n[{b.type}] {b.model_dump() if hasattr(b, 'model_dump') else b}")

    if result.get("error"):
        print(f"\nERROR: {result['error']}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Debug the Customer 360 agent trace.")
    parser.add_argument("question", nargs="*", help="the question to debug")
    parser.add_argument("--no-raw", action="store_true",
                        help="omit raw LLM JSON from the output")
    args = parser.parse_args()

    question = " ".join(args.question).strip()
    if not question:
        question = input("Question: ").strip()
    if not question:
        print("No question given.", file=sys.stderr)
        sys.exit(2)

    sys.exit(asyncio.run(main(question, raw=not args.no_raw)))
