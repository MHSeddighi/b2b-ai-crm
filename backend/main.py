"""FastAPI entrypoint for the Customer 360 backend.

Exposes a single JSON endpoint `/api/chat` that the frontend copilot calls.
Each request spawns a short-lived MCP session to the DuckDB server and, when an
LLM key is configured, answers the question with a live database query.
"""
from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

# neutralise stray proxies before any outbound call
for _v in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
           "http_proxy", "https_proxy", "all_proxy"):
    os.environ.pop(_v, None)

from backend.agents import db_agent
from backend import api_data
from backend.config import settings


@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield
    # One clean shutdown of the persistent MCP server at app exit.
    await db_agent.close_mcp()


app = FastAPI(title="Customer 360 Copilot", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    # Optional conversation history: [{"role": "user"|"assistant", "content": "..."}]
    history: list[dict[str, Any]] = Field(default_factory=list)
    # Optional session id: enables bounded per-session state + result reuse.
    session_id: str | None = None
    # When true, responses include the full agent trace (LLM calls, plans,
    # tool calls and results, session state) for debugging.
    debug: bool = False


class ChatResponse(BaseModel):
    blocks: list[Any] = []
    results: dict[str, Any] = {}
    query: str | None = None
    columns: list[str] = []
    rows: list[list[Any]] = []
    n_rows: int = 0
    trace: list[Any] = []


@app.get("/api/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "db": str(settings.db_path),
        "db_exists": settings.db_path.exists(),
        "provider": settings.provider,
        "model": settings.resolved_model,
        "llm_configured": settings.has_key,
    }


@app.get("/api/dashboard")
async def dashboard() -> dict[str, Any]:
    return api_data.dashboard()


@app.get("/api/analyses")
async def analyses() -> dict[str, Any]:
    """Real, computed analyses for the Analyses page (no LLM)."""
    return api_data.analyses()


@app.get("/api/dashboard/intelligence")
async def dashboard_intelligence(refresh: bool = False) -> dict[str, Any]:
    """LLM portfolio summary for the dashboard (cached; refresh=1 regenerates)."""
    from backend.agents import intel_summary
    det = api_data.dashboard()
    return await intel_summary.dashboard_summary(det, refresh=refresh)


@app.get("/api/customers")
async def customers() -> dict[str, Any]:
    return {"customers": api_data.customers()}


@app.get("/api/customers/{customer_id}/360")
async def customer_360(customer_id: str) -> dict[str, Any] | None:
    return api_data.customer_360(customer_id)


@app.get("/api/customers/{customer_id}/360/summary")
async def customer_360_summary(customer_id: str,
                               refresh: bool = False) -> dict[str, Any]:
    """LLM intelligence summary for one customer (cached; refresh=1 regenerates)."""
    from backend.agents import intel_summary
    payload = api_data.customer_360(customer_id)
    if payload is None:
        return {"status": "not_found", "summary": None, "generated": False}
    return await intel_summary.customer_summary(payload, refresh=refresh)


# --- Deterministic Customer Intelligence (Signal -> State -> Action) ---
@app.get("/api/customers/{customer_id}/intelligence")
async def customer_intelligence(customer_id: str) -> dict[str, Any]:
    """Canonical customer-intelligence object (signals + state + reasons +
    next-best actions + data quality), computed entirely in the backend."""
    from backend.crm.service import service
    return service.get_intelligence(customer_id).model_dump()


@app.get("/api/customers/{customer_id}/signals")
async def customer_signals(customer_id: str) -> dict[str, Any]:
    from backend.crm.service import service
    return {k: v.model_dump() for k, v in service.get_signals(customer_id).items()}


@app.get("/api/customers/{customer_id}/state")
async def customer_state(customer_id: str) -> dict[str, Any] | None:
    from backend.crm.service import service
    st = service.get_state(customer_id)
    return st.model_dump() if st else None


@app.get("/api/customers/{customer_id}/reasons")
async def customer_reasons(customer_id: str) -> list[dict[str, Any]]:
    from backend.crm.service import service
    return [r.model_dump() for r in service.get_reasons(customer_id)]


@app.get("/api/customers/{customer_id}/next-best-actions")
async def customer_next_best_actions(customer_id: str) -> list[dict[str, Any]]:
    from backend.crm.service import service
    return [a.model_dump() for a in service.get_next_best_actions(customer_id)]


@app.get("/api/customers/{customer_id}/action-plan")
async def customer_action_plan(customer_id: str) -> dict[str, Any]:
    from backend.crm.service import service
    return service.get_action_plan(customer_id)


@app.post("/api/chat")
async def chat(req: ChatRequest) -> ChatResponse:
    result = await db_agent.answer(req.question, history=req.history,
                                   session_id=req.session_id, debug=req.debug)
    blocks = [b.model_dump() for b in result.get("blocks", [])]
    results = {
        k: v.model_dump() if hasattr(v, "model_dump") else v
        for k, v in result.get("results", {}).items()
    }
    return ChatResponse(
        blocks=blocks,
        results=results,
        query=result.get("query"),
        columns=result.get("columns", []),
        rows=result.get("rows", []),
        n_rows=result.get("n_rows", 0),
        trace=result.get("trace", []),
    )


@app.post("/api/chat/stream")
async def chat_stream(req: ChatRequest) -> StreamingResponse:
    """SSE stream: the answer text arrives token-by-token, then structured
    blocks (charts/tables/metrics) and results are sent at the end."""

    async def event_source():
        # Run the answer producer in its own task feeding a queue, so we can
        # emit SSE keep-alive comment lines whenever it is quiet (the producer
        # is suspended during long LLM calls). This keeps the connection
        # clearly alive and prevents idle-based timeouts mid-answer.
        import asyncio

        q: asyncio.Queue = asyncio.Queue()

        async def producer():
            try:
                async for event in db_agent.answer_stream(
                    req.question,
                    history=req.history,
                    session_id=req.session_id,
                    debug=req.debug,
                ):
                    await q.put(("event", event))
            except Exception as exc:  # noqa: BLE001 - never leave the stream hanging
                await q.put(("error", exc))
            finally:
                await q.put(("done", None))

        task = asyncio.create_task(producer())
        try:
            while True:
                try:
                    kind, payload = await asyncio.wait_for(q.get(), timeout=15)
                except asyncio.TimeoutError:
                    # Keep-alive comment line — ignored by the SSE client.
                    yield ": ping\n\n"
                    continue
                if kind == "done":
                    break
                if kind == "error":
                    yield f"data: {json.dumps({'type': 'error', 'message': f'خطا در دریافت پاسخ: {payload}'}, ensure_ascii=False)}\n\n"
                    break
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
        finally:
            task.cancel()

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
