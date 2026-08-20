#!/usr/bin/env python3
"""Benchmark common Customer 360 copilot requests.

Measures wall latency, number of LLM calls, number of SQL (MCP) tool calls, and
prompt size for a set of common questions against the real backend (DuckDB MCP +
DeepSeek LLM). Used to verify the speed / token / tool-call optimizations.

Usage:
    .venv/bin/python scripts/benchmark_agent.py [--repeat N]
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

for _v in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
           "http_proxy", "https_proxy", "all_proxy"):
    os.environ.pop(_v, None)

from backend.agents import db_agent  # noqa: E402

QUESTIONS = [
    ("chat", "سلام"),
    ("count", "چند مشتری داریم؟"),
    ("top_customers", "برترین مشتریان از نظر درآمد کدامند؟"),
    ("sales_trend", "روند فروش ماهانه را نشان بده"),
    ("complaints", "پرتکرارترین دلایل شکایت چیست؟"),
]


def _estimate_tokens(chars: int) -> int:
    return max(1, chars // 4)


def main(repeat: int) -> None:
    orig_chat = db_agent._llm_call
    orig_run = db_agent._run_sql

    print(f"{'request':<14}{'latency':>8}{'LLM':>5}{'SQL':>5}{'~tok':>7}  blocks / error")

    # The MCP server is a persistent singleton tied to ONE event loop, so all
    # requests must run in the same asyncio.run() instead of a fresh loop each.
    async def run_all():
        for name, q in QUESTIONS:
            calls_llm: list[int] = []
            calls_sql: list[str] = []
            min_time = float("inf")
            last_res = None

            def chat_wrap(system, user, temperature=0.0):
                # total prompt size (system + user) across the call
                calls_llm.append(len(str(system)) + len(str(user)))
                return orig_chat(system, user, temperature=temperature)

            async def run_wrap(session, sql):
                calls_sql.append(sql)
                return await orig_run(session, sql)

            db_agent._llm_call = chat_wrap
            db_agent._run_sql = run_wrap
            try:
                for _ in range(repeat):
                    db_agent.clear_sessions()
                    sid = f"bench-{name}-{int(time.time() * 1000)}"
                    t0 = time.perf_counter()
                    last_res = await db_agent.answer(q, session_id=sid)
                    min_time = min(min_time, time.perf_counter() - t0)
            finally:
                db_agent._llm_call = orig_chat
                db_agent._run_sql = orig_run

            blocks = [b.type for b in last_res.get("blocks", [])] if last_res else []
            tokens = sum(_estimate_tokens(c) for c in calls_llm)
            print(f"{name:<14}{min_time:>7.2f}s{len(calls_llm):>5}{len(calls_sql):>5}"
                  f"{tokens:>7}  {','.join(blocks)}"
                  + (f"  ERROR: {last_res.get('error')}" if last_res and last_res.get('error') else ""))

    asyncio.run(run_all())
    asyncio.run(db_agent.close_mcp())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--repeat", type=int, default=1)
    args = ap.parse_args()
    main(args.repeat)
