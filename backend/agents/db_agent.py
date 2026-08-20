from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from openai import AsyncOpenAI, OpenAI

from backend.agents import contracts
from backend.agents.analysis import is_huge, too_huge_message
from backend.agents.context import SessionState, answer_preview
from backend.agents.contracts import CRM_TOOLS
from backend.agents.trace import Trace
from backend.config import settings
from backend.mcp.schema_context import CUSTOMER360_SCHEMA
from backend.schemas.blocks import BLOCK_TYPES, SqlResult, validate_blocks


for key in (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
):
    os.environ.pop(key, None)


MAX_SESSIONS = 200
MAX_QUERIES = 3
_SESSIONS: dict[str, SessionState] = {}

BLOCK_TYPES_TEXT = ", ".join(sorted(BLOCK_TYPES))


BUSINESS_RULES = """
- Use realized_costs for actual cost; monthly_costs is estimated.
- Customer_ID uniquely identifies a customer.
- For CRM interactions, use the latest Record_Version for each Interaction_ID.
- Respect Available_At when using records.
- Hembaft_ID and Lot_ID are different; join through Hembaft_Lot_Key.
- Use 'مبلغ کل' for sales revenue.
- COUNT(DISTINCT order_id) = orders.
- SUM(quantity) = units sold.
- Never double-count orders because of joins.
- Some columns are Persian YES/NO TEXT values, not integers. For example
  'چک برگشتی' (in the collections table) is VARCHAR with values 'بله'/'خیر'.
  Filter them with string literals: WHERE "چک برگشتی" = 'بله'. Never cast a
  text/VARCHAR column to INT or compare it to a number; if a column's value
  looks like Persian yes/no text, treat it as text.
- Avoid DuckDB reserved keywords as column aliases, CTE names, or table aliases
  (e.g. asof, range, qualify, sample, struct, struct_extract, current,
  latest, and similar). Use simple, safe aliases instead: t1, base, max_date,
  sales_m, month_label, total_amt.
"""


PLANNER_SYSTEM = f"""You are the Customer 360 reasoning agent.

Your job is to decide what is needed to answer the user's question.

Available tools:
- query: run a read-only SQL query against the DuckDB database.
  input: {{"query": "<SQL>", "purpose": "<short reason>"}}
- reuse: use an existing result from an earlier turn in this conversation.
  input: {{"resultId": "<existing result id>", "purpose": "<short reason>"}}
- get_customer_signals: all backend-calculated signals for one customer.
  input: {{"customer_id": "<Customer_ID>"}}
- get_customer_state: derived customer state (value/risk/health/opportunity).
  input: {{"customer_id": "<Customer_ID>"}}
- get_customer_reasons: structured evidence/reasons for a customer.
  input: {{"customer_id": "<Customer_ID>"}}
- get_next_best_actions: backend-approved, eligible + ranked actions.
  input: {{"customer_id": "<Customer_ID>"}}
- get_customer_action_plan: full recommendation context for a customer.
  input: {{"customer_id": "<Customer_ID>"}}
- top_at_risk_customers: rank customers by churn-risk and return the top N.
  Use for "which customers are at risk / likely to churn" questions.
  input: {{"limit": 10}}

CRITICAL ROUTING RULES:
- For customer-specific recommendations, churn/risk, growth opportunity,
  "what should we do with customer X", next best actions, or any signal
  (profit, trend, payment, share of wallet, cycle, margin, complaints,
  offers), use the CRM tools above. NEVER write SQL or invent these numbers.
- For "which customers are at risk / likely to churn / should be watched" across
  ALL customers, use top_at_risk_customers with a small limit (e.g. 10), NOT
  SQL. Do not try to compute the risk yourself.
- Use the query tool only for factual lookups / aggregations that the CRM
  tools do not cover.
- The CRM tools return backend-computed values; you must not invent or
  recalculate any signal, score, threshold, or action.
- If a CRM tool returns no data (e.g. customer not found, unknown signal),
  say the data is insufficient — never guess.

Database schema:
{CUSTOMER360_SCHEMA}

Data rules:
{BUSINESS_RULES}

Return ONLY valid JSON:

{{
  "intent": "short description",
  "steps": [
    {{
      "tool": "tool_name",
      "input": {{}}
    }}
  ],
  "assumption": "",
  "state": {{}}
}}

Rules:
- Use the minimum number of tools needed.
- Prefer one tool; use more only when necessary.
- Use an existing result when it already contains the required information (reuse).
- If no tool is needed, return an empty steps array.
- Never invent tool names or inputs.
- Do not answer the user; only create the execution plan.
- Keep the plan simple and focused.
- Never guess data; if the question is ambiguous, pick a sensible assumption and put it in "assumption".
- Keep the result small: filter, join, aggregate, sort and LIMIT inside the SQL.
- For "which / top N / who is at risk" ranking questions, ALWAYS ORDER BY the
  risk or relevant metric DESC and LIMIT a small number (e.g. LIMIT 10 or 20)
  inside the SQL so the result stays small. Never select the whole table.
- For orders use COUNT(DISTINCT order_id); orders ≠ lines ≠ units.
- SQL must be read-only and start with SELECT or WITH.
- If the question needs more than one query or may return a large result, that
  is fine — plan it. The assistant will let the user know it is processing in a
  few steps.
"""


COMPOSER_SYSTEM = f"""You are a senior business analyst.

Answer the user's question using the provided results.

The user does not know the database, columns, SQL, or technical terminology.

Allowed block types:
{BLOCK_TYPES_TEXT}

Block JSON shapes (field names are EXACT — do not rename them):
- markdown: {{"type":"markdown","content":"..."}}
- metric:   {{"type":"metric","label":"...","valueKey":"<col>","resultId":"<id>","rowIndex":0}}
- chart:    {{"type":"chart","resultId":"<id>","chartType":"line","xKey":"<col>","series":[{{"dataKey":"<col>","label":"..."}}],"title":"..."}}
- table:    {{"type":"table","columns":["a","b"],"rows":[["x","y"]]}}  (or reference a result with "resultId")
- recommendation: {{"type":"recommendation","title":"...","text":"...","reason":"..."}}

Rules:
- Answer directly first.
- Explain what the result means in simple business language.
- Give a short explanation of the analysis: why the numbers look the way they
  do, what they indicate about the business, and what the data is based on —
  tailored to what the user asked.
- Highlight an important pattern or implication when useful.
- Never mention SQL, tables, columns, result IDs, or internal tools.
- Never invent or recalculate numbers.
- If the data is insufficient, say so clearly.
- Do not use headings like "Insight", "Finding", or "Analysis".
- Keep the answer concise and natural.
- When the results are numeric or a trend, always add a chart, metric, or table
  to visualize them — do not leave numbers as plain text alone.
- If there is an assumption, reflect it naturally and briefly in the answer.
- Use the "markdown" type for prose (never "text"; the content field is
  "content"). Use "columns" (never "headers") in tables.
"""


CHAT_SYSTEM = """
تو دستیار Customer 360 هستی.
به فارسی و طبیعی صحبت کن.
کوتاه و مستقیم پاسخ بده.
از اصطلاحات فنی غیرضروری استفاده نکن.
اگر کاربر از «قطع شدن ارتباط»، «ارتباط با سرور»، «سرور پشتیبان»، «نتونست وصل بشه» یا
خطاهای مشابه در حین پاسخ‌گویی می‌پرسد، این مربوط به سرویس پشتیبان داخلی است، نه اینترنت
یا تلفن کاربر. عذرخواهی کن، توضیح بده که به‌طور موقت اختلالی پیش آمده و دوباره سؤالش را
بپرسد یا دوباره تلاش کند؛ از پرسیدن درباره اینترنت/سرویس‌دهنده خودداری کن.
"""


# Streaming narrative prompt: produces ONLY the natural-language answer as
# plain text (token-by-token). Structured blocks (charts/tables/metrics) are
# produced separately afterwards so the long text can stream in immediately.
NARRATIVE_SYSTEM = f"""You are a senior business analyst.

Answer the user's question using the provided results.

The user does not know the database, columns, SQL, or technical terminology.

Rules:
- Answer directly and naturally in the user's language.
- Explain what the result means in simple business language.
- Give a short explanation of the analysis: why the numbers look the way they
  do, what they indicate about the business, and what the data is based on —
  tailored to what the user asked.
- Highlight an important pattern or implication when useful.
- Never mention SQL, tables, columns, result IDs, or internal tools.
- Never invent or recalculate numbers.
- If the data is insufficient, say so clearly.
- Do not use headings like "Insight", "Finding", or "Analysis".
- Keep the answer concise and natural.
- Return ONLY plain prose. NEVER output markdown tables, numbered/dashed row
  lists, or ASCII/Unicode bar charts (e.g. █ ██ ▌) — any tabular data, ranking,
  or distribution is rendered by the chart/table/histogram blocks, so keep the
  text as a readable summary and interpretation, not a re-rendered table.
- When the answer is large or took multiple steps (big data, several queries),
  briefly tell the user at a friendly level what is happening (e.g. "داده‌ها
  بزرگ است و پاسخ در چند مرحله آماده شد…") and then continue. Keep such notes
  short and natural.
- When discussing churn, at-risk customers, retention, or recommendations,
  briefly say the assessment is based on the CRM's customer-intelligence
  signals (complaint volume, purchase recency, order volume, bounced checks)
  and the risk-scoring algorithm, then explain which signals drive the risk for
  the specific customers. Do this naturally in the user's language.

RECOMMENDATION SAFETY RULES (mandatory):
- Never invent CRM metrics, customer signals, business conditions,
  recommendations, thresholds, or actions.
- For customer-specific recommendations, use ONLY the values returned by the
  CRM signal/action tools (get_customer_signals / get_customer_state /
  get_customer_reasons / get_next_best_actions / get_customer_action_plan).
- You may explain, summarize, prioritize, and personalize backend-approved
  recommendations, but you must NOT create a recommendation that is not
  present in the tool output.
- If the required tool data is unavailable or insufficient, say so explicitly
  and do not guess.
"""


def _blocks_system(result_ids: str) -> str:
    return f"""You are a data visualization assistant.

Given the results, pick the most useful blocks. When results are numeric or
tabular, ALWAYS add a visualization/card — never leave numbers as plain text.
Return [] only for purely conversational answers. Use ONLY the available
resultIds below; column names and id values must match the results EXACTLY
(never rename them).

Available resultIds:
{result_ids}

Return ONLY a JSON array of blocks. Every block needs a unique "id" and
(except recommendation) "resultId". Shapes:

1. metric — one headline number:
   {{"type":"metric","id":"m1","resultId":"<id>","label":"فروش کل","valueKey":"<exact column>","rowIndex":0,"trend":"up"}}

2. chart — trend/category comparison: "line" for time trends, "bar" for categories, "scatter" for correlation:
   {{"type":"chart","id":"c1","resultId":"<id>","chartType":"line","xKey":"<exact column>","series":[{{"dataKey":"<exact column>","label":"فروش"}}],"title":"روند فروش ماهانه"}}

3. histogram — distribution of ONE numeric column (use when asked for histogram/distribution):
   {{"type":"histogram","id":"h1","resultId":"<id>","dataKey":"<exact numeric column>","bins":10,"title":"توزیع فروش"}}

4. table — ranked lists / multi-row detail:
   {{"type":"table","id":"t1","resultId":"<id>","title":"برترین مشتریان"}}

5. customer_card — one specific customer (1-row result):
   {{"type":"customer_card","id":"cc1","resultId":"<id>","customerId":"<exact Customer_ID value>"}}

6. product_card — one specific product (1-row result):
   {{"type":"product_card","id":"pc1","resultId":"<id>","productId":"<exact Product_ID value>"}}

7. order_card — line items of one order:
   {{"type":"order_card","id":"oc1","resultId":"<id>","orderId":"<exact order id>"}}

8. recommendation — suggested action (no resultId):
   {{"type":"recommendation","id":"r1","title":"پیشنهاد","text":"...","reason":"..."}}

Rules:
- line chart for time trends; bar/table for categories; histogram when the user
  asks for a distribution/histogram; metric for a single headline number;
  customer_card/product_card/order_card for a single named entity (1-row result);
  table for ranked lists or multi-column detail.
- xKey, series[].dataKey, valueKey, dataKey must be EXACT result column names;
  if unsure which column to use, take the FIRST for the x-axis and the SECOND
  for the series.
- Never invent numbers. Usually 1-2 blocks, at most 3.
"""


def _get_session(session_id: str) -> SessionState:
    if session_id not in _SESSIONS:
        _SESSIONS[session_id] = SessionState(session_id)

    _SESSIONS[session_id] = _SESSIONS.pop(session_id)

    while len(_SESSIONS) > MAX_SESSIONS:
        _SESSIONS.pop(next(iter(_SESSIONS)))

    return _SESSIONS[session_id]


def clear_sessions() -> None:
    _SESSIONS.clear()


def _llm_client() -> OpenAI:
    if not settings.has_key:
        raise RuntimeError("LLM is not configured")

    return OpenAI(
        api_key=settings.api_key,
        base_url=settings.resolved_base_url,
    )


def _llm_call(
    system: str,
    user: str,
    temperature: float = 0.0,
) -> str:
    response = _llm_client().chat.completions.create(
        model=settings.resolved_model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=temperature,
    )

    return response.choices[0].message.content or ""


async def _llm_call_async(
    system: str,
    user: str,
    temperature: float = 0.0,
    trace: Trace | None = None,
    call: str = "llm",
) -> str:
    """Run the blocking LLM call off the event loop.

    ``_llm_call`` performs a synchronous HTTP request (DeepSeek latency can be
    30-76s). Calling it directly inside an async handler freezes the whole
    uvicorn event loop — every other request (including the SSE stream itself
    and /api/health) stalls. Running it via ``asyncio.to_thread`` keeps the
    loop responsive while the LLM thinks.
    """
    t0 = time.monotonic()
    raw = await asyncio.to_thread(_llm_call, system, user, temperature)
    if trace is not None:
        trace.llm(
            call=call, model=settings.resolved_model,
            input_chars=len(system) + len(user), output_chars=len(raw or ""),
            latency_ms=int((time.monotonic() - t0) * 1000), raw=raw,
        )
    return raw


# ---------------------------------------------------------------------------
# Persistent MCP server
#
# We keep ONE long-lived DuckDB MCP server for the whole app process instead of
# spawning/tearing one down per request (which was slow and printed noisy
# ProcessLookupError tracebacks on teardown).
#
# Important: the MCP stdio_client is an anyio async context manager whose cancel
# scope is bound to the *task* that enters it. Entering it in a request task and
# exiting it in a different task (e.g. the app shutdown task, or the streaming
# response's collapsing task group) raises "Attempted to exit a cancel scope
# that isn't the current task's current cancel scope". So we enter+exit it in a
# SINGLE dedicated background task that lives for the app's lifetime; requests
# only call ``session.call_tool`` (sending/receiving on memory streams), which
# is safe from any task while the worker keeps the reader/writer tasks alive.
# ---------------------------------------------------------------------------
_mcp_worker: asyncio.Task | None = None
_mcp_session: ClientSession | None = None
_mcp_ready: asyncio.Event | None = None
_mcp_stop: asyncio.Event | None = None
_mcp_lock: asyncio.Lock | None = None


def _mcp_params() -> StdioServerParameters:
    return StdioServerParameters(
        command=sys.executable,
        args=["-m", "backend.mcp.duckdb_server"],
        env=dict(os.environ),
    )


async def _mcp_worker_loop() -> None:
    """Own the stdio_client context for its whole life (started once)."""
    global _mcp_session
    streams = stdio_client(_mcp_params())
    read, write = await streams.__aenter__()
    session = ClientSession(read, write)
    await session.__aenter__()
    await session.initialize()
    _mcp_session = session
    _mcp_ready.set()
    try:
        await _mcp_stop.wait()
    finally:
        _mcp_session = None
        try:
            await session.__aexit__(None, None, None)
        except Exception:  # noqa: BLE001 - shutdown must not raise
            pass
        try:
            await streams.__aexit__(None, None, None)
        except Exception:  # noqa: BLE001 - shutdown must not raise
            pass


async def _ensure_mcp() -> ClientSession:
    """Return the app-wide MCP session, starting the server exactly once.

    Safe to call from concurrent request handlers: the first caller starts the
    worker, everyone else awaits the ready event and reuses the session.
    """
    global _mcp_worker, _mcp_ready, _mcp_stop, _mcp_lock
    if _mcp_session is not None:
        return _mcp_session
    if _mcp_lock is None:
        _mcp_lock = asyncio.Lock()
    async with _mcp_lock:
        if _mcp_session is not None:
            return _mcp_session
        _mcp_ready = asyncio.Event()
        _mcp_stop = asyncio.Event()
        _mcp_worker = asyncio.create_task(_mcp_worker_loop())
    await _mcp_ready.wait()
    if _mcp_session is None:
        raise RuntimeError("MCP server failed to start")
    return _mcp_session


async def close_mcp() -> None:
    """Tear down the persistent MCP server (call once on app shutdown)."""
    global _mcp_worker, _mcp_stop
    worker, _mcp_worker = _mcp_worker, None
    stop, _mcp_stop = _mcp_stop, None
    if stop is not None:
        stop.set()
    if worker is not None:
        try:
            await asyncio.wait_for(worker, timeout=5)
        except Exception:  # noqa: BLE001 - best-effort shutdown
            worker.cancel()


async def _restart_mcp() -> None:
    """Tear down a dead MCP server so the next ``_ensure_mcp`` starts fresh.

    Safe under concurrent calls: everything happens under ``_mcp_lock``, so
    only one request performs the restart while the others block until the
    fresh session is ready.
    """
    global _mcp_lock
    if _mcp_lock is None:
        _mcp_lock = asyncio.Lock()
    async with _mcp_lock:
        if _mcp_session is not None:
            await close_mcp()


async def _call_query(session: ClientSession, sql: str) -> dict[str, Any]:
    response = await session.call_tool(
        "query",
        {"query": sql},
    )

    text = "".join(
        getattr(item, "text", "") or ""
        for item in response.content
    )

    return json.loads(text)


async def _call_crm_tool(session: ClientSession, tool: str,
                         args: dict[str, Any],
                         trace: Trace | None = None) -> dict[str, Any]:
    """Invoke a deterministic CRM tool and parse its JSON result."""
    t0 = time.monotonic()
    response = await session.call_tool(tool, args)
    text = "".join(
        getattr(item, "text", "") or ""
        for item in response.content
    )
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Preserve non-JSON output as a raw string result for safe display.
        data = {"_raw": text}
    if trace is not None:
        trace.tool(tool, args, data, int((time.monotonic() - t0) * 1000), ok=True)
    return data


async def _run_sql(sql: str) -> dict[str, Any]:
    """Execute ``sql`` against the shared MCP session.

    Resolves the session internally (never a stale reference) and, if the MCP
    server died mid-request (backend reload, subprocess crash), restarts it
    once and retries the query before giving up.
    """
    session = await _ensure_mcp()
    try:
        return await _call_query(session, sql)
    except Exception:
        await _restart_mcp()
        session = await _ensure_mcp()
        return await _call_query(session, sql)


_SQL_FIX_SYSTEM = """You fix a failing DuckDB SQL query.
Return ONLY the corrected SQL (one read-only statement starting with SELECT or
WITH). No explanation, no markdown fences. Keep the same intent and result
columns. Common causes of the error:
- DuckDB reserved keywords used as identifiers/aliases (e.g. asof, range,
  qualify, sample, struct) — rename them to simple aliases like t1, base,
  max_date, total_amt.
- Casting a text/VARCHAR column (e.g. a Persian yes/no column like 'چک برگشتی'
  with values 'بله'/'خیر') to INT — filter with string literals instead.
- Wrong date function: use strftime(x, '%Y-%m') for formatting, CAST(col AS DATE)
  for date math; single quotes for strings, double quotes for identifiers."""


def _sql_fix_prompt(question: str, sql: str, error: str) -> str:
    return f"""A DuckDB query failed. Fix it so it runs correctly.

User question:
{question}

Failing SQL:
{sql}

Error:
{error}

Return ONLY the corrected SQL."""


async def _fix_sql(question: str, sql: str, error: str) -> str | None:
    """Ask the LLM to rewrite a failing SQL query once. None if it can't."""
    try:
        raw = await _llm_call_async(_SQL_FIX_SYSTEM, _sql_fix_prompt(question, sql, error), temperature=0.0)
    except Exception:  # noqa: BLE001 - best effort
        return None
    fixed = (raw or "").strip().strip("`")
    lowered = fixed.lower()
    if not (lowered.startswith("select") or lowered.startswith("with")):
        return None
    return fixed


async def _exec_query(question: str, sql: str,
                      trace: Trace | None = None) -> dict[str, Any]:
    """Run a query; if it returns an SQL error, ask the LLM to fix it once and
    retry. Returns the original error if the fix doesn't help or the query is
    genuinely bad, so failures stay explicit instead of silent."""
    t0 = time.monotonic()
    data = await _run_sql(sql)
    if not data.get("error"):
        if trace is not None:
            trace.tool("query", {"sql": sql}, data,
                       int((time.monotonic() - t0) * 1000), ok=True)
        return data
    fixed = await _fix_sql(question, sql, data["error"])
    if fixed and fixed.strip().lower() != sql.strip().lower():
        data2 = await _run_sql(fixed)
        if not data2.get("error"):
            if trace is not None:
                trace.tool("query", {"sql": sql, "fixed_sql": fixed}, data2,
                           int((time.monotonic() - t0) * 1000), ok=True)
            return data2
    if trace is not None:
        trace.tool("query", {"sql": sql}, data,
                   int((time.monotonic() - t0) * 1000), ok=False,
                   error=data.get("error", ""))
    return data


def _plan_prompt(
    question: str,
    ctx: SessionState,
) -> str:
    context = ctx.render_context(
        question,
        active_ids=ctx.active_result_ids(),
    )

    return f"""
User question:
{question}

Relevant conversation context (includes earlier results referenced by their
resultId):
{context}

Decide the minimal execution plan. Reuse an existing result when it already
contains the answer; otherwise query for exactly what is missing. If no data
is needed, return an empty steps array.

Return ONLY valid JSON.
"""


def _plan_from_raw(raw: str) -> dict[str, Any]:
    plan = contracts.parse_plan(raw)
    return {
        "intent": plan.intent,
        "assumption": plan.assumption,
        "state": plan.state or {},
        "steps": contracts.plan_steps(plan, MAX_QUERIES),
    }


async def _plan(
    question: str,
    ctx: SessionState,
    trace: Trace | None = None,
) -> dict[str, Any]:
    raw = await _llm_call_async(
        PLANNER_SYSTEM,
        _plan_prompt(question, ctx),
        temperature=0.0,
        trace=trace,
        call="planner",
    )
    plan = _plan_from_raw(raw)
    if trace is not None:
        trace.plan(plan["intent"], plan["steps"], plan["assumption"])
    return plan


async def _plan_stream(
    question: str,
    ctx: SessionState,
    trace: Trace | None = None,
) -> Any:
    """Stream the planner's reasoning as raw deltas, then yield the parsed plan.

    The async generator first yields ``("thinking", delta)`` tuples for every
    token of the planner's JSON, then a final ``("plan", dict)`` tuple.
    """
    raw = ""
    t0 = time.monotonic()
    prompt = _plan_prompt(question, ctx)
    async for delta in _llm_stream(
        PLANNER_SYSTEM,
        prompt,
        temperature=0.0,
    ):
        raw += delta
        yield ("thinking", delta)
    if trace is not None:
        trace.llm(
            call="planner_stream", model=settings.resolved_model,
            input_chars=len(PLANNER_SYSTEM) + len(prompt),
            output_chars=len(raw), latency_ms=int((time.monotonic() - t0) * 1000),
            raw=raw,
        )
    plan = _plan_from_raw(raw)
    if trace is not None:
        trace.plan(plan["intent"], plan["steps"], plan["assumption"])
    yield ("plan", plan)


def _render_crm(crm_results: dict[str, Any]) -> str:
    """Render deterministic CRM tool results as a compact JSON block."""
    if not crm_results:
        return ""
    parts: list[str] = []
    for key, data in crm_results.items():
        js = json.dumps(data, ensure_ascii=False, default=str)
        parts.append(f"CRM result [{key}]:\n{js[:2500]}")
    return "\n\n".join(parts)


def _compose_prompt(
    question: str,
    ctx: SessionState,
    results: dict[str, SqlResult],
    assumption: str,
    crm_results: dict[str, Any] | None = None,
) -> str:
    context = ctx.render_context(
        question,
        active_ids=[],
    )

    samples = ctx.result_samples(
        list(results.keys())
    )

    crm_block = _render_crm(crm_results or {})

    return f"""
User question:
{question}

Conversation context:
{context}

Assumption:
{assumption or "none"}

Results:
{samples}

Deterministic customer intelligence (backend-computed, do NOT recalculate or
invent; use these values verbatim for any recommendation):
{crm_block or "(none)"}

Answer the user's question using these results. The user does not know the
database, columns, SQL, or technical terminology.

Return ONLY the required JSON blocks.
"""


async def _compose(
    question: str,
    ctx: SessionState,
    results: dict[str, SqlResult],
    assumption: str,
    crm_results: dict[str, Any] | None = None,
    trace: Trace | None = None,
) -> list[dict]:
    raw = await _llm_call_async(
        COMPOSER_SYSTEM,
        _compose_prompt(
            question,
            ctx,
            results,
            assumption,
            crm_results,
        ),
        temperature=0.2,
        trace=trace,
        call="composer",
    )

    parsed = contracts.parse_blocks_json(raw)

    if isinstance(parsed, list):
        return parsed

    return [
        {
            "id": "b1",
            "type": "markdown",
            "content": str(raw),
        }
    ]


def _error(
    message: str,
    results: dict[str, SqlResult] | None = None,
) -> dict[str, Any]:
    return {
        "blocks": validate_blocks(
            [
                {
                    "id": "b1",
                    "type": "markdown",
                    "content": message,
                }
            ]
        ),
        "results": results or {},
        "error": message,
    }


async def _chat_answer(
    question: str,
    ctx: SessionState,
) -> dict[str, Any]:
    raw = await _llm_call_async(
        CHAT_SYSTEM,
        ctx.render_context(question),
        temperature=0.4,
    )

    return {
        "blocks": validate_blocks(
            [
                {
                    "id": "b1",
                    "type": "markdown",
                    "content": raw,
                }
            ]
        ),
        "results": {},
    }


async def _database_answer(
    question: str,
    ctx: SessionState,
    trace: Trace | None = None,
) -> dict[str, Any]:
    if trace is not None:
        trace.meta(session_id=ctx.session_id, question=question)
        trace.stage("planning", "شروع تحلیل سؤال")

    try:
        plan = await _plan(question, ctx, trace)
    except Exception as exc:
        return _error(f"خطا در تحلیل سؤال: {exc}")

    steps = plan["steps"]

    # No tools needed -> plain conversational answer.
    if not steps:
        return await _chat_answer(question, ctx)

    results: dict[str, SqlResult] = {}
    crm_results: dict[str, Any] = {}

    for step in steps:
        kind = step["kind"]

        if kind == "reuse":
            result_id = step["resultId"]
            if not result_id:
                return _error("نتیجه قبلی مشخص نشد.")
            result = ctx.get_result(result_id)
            if result is None:
                return _error(
                    "اطلاعات موردنیاز از نتیجه قبلی دیگر در دسترس نیست."
                )
            results[result_id] = result

        elif kind == "query":
            sql = (step["sql"] or "").strip()
            if not sql:
                return _error("برای این سؤال اطلاعاتی برای جستجو تولید نشد.")

            normalized = sql.lstrip().lower()
            if not normalized.startswith(("select", "with")):
                return _error("کوئری تولیدشده مجاز نیست.")

            if trace is not None:
                trace.stage("query", "در حال اجرای پرس‌وجو", sql[:200])
            try:
                data = await _exec_query(question, sql, trace)
            except Exception as exc:
                return _error(f"خطا در دریافت اطلاعات: {exc}")

            if data.get("error"):
                return _error(f"خطا در دریافت اطلاعات: {data['error']}")

            result_id = data.get("resultId") or "r1"

            results[result_id] = ctx.add_result(
                result_id,
                step.get("purpose") or "",
                data.get("columns", []),
                data.get("rows", []),
                data.get("n_rows"),
            )
            if trace is not None:
                trace.result(result_id, step.get("purpose") or "",
                             data.get("columns", []), data.get("n_rows", 0))

        elif kind == "crm":
            tool = step.get("tool") or ""
            customer_id = step.get("customer_id") or ""
            if tool not in CRM_TOOLS:
                return _error("درخواست سیگنال/اقدام مشتری نامعتبر است.")
            if tool == "top_at_risk_customers":
                args: dict[str, Any] = {"limit": int(step.get("limit") or 10)}
            elif not customer_id:
                return _error("درخواست سیگنال/اقدام مشتری نامعتبر است.")
            else:
                args = {"customer_id": customer_id}
            if trace is not None:
                trace.stage("crm_tool", f"در حال دریافت نتایج {tool}", customer_id or str(args))
            try:
                data = await _call_crm_tool(await _ensure_mcp(), tool, args, trace)
            except Exception as exc:  # noqa: BLE001
                return _error(f"خطا در دریافت اطلاعات مشتری: {exc}")
            key = f"{tool}:{customer_id or args.get('limit')}"
            crm_results[key] = data

        else:
            return _error("نوع درخواست قابل تشخیص نیست.")

    huge = next(
        (
            (result_id, result.n_rows)
            for result_id, result in results.items()
            if is_huge(result.n_rows)
        ),
        None,
    )

    if huge:
        result_id, count = huge

        return {
            "blocks": validate_blocks(
                [
                    {
                        "id": "b1",
                        "type": "markdown",
                        "content": (
                            too_huge_message(count)
                            + "\n\n"
                            + f"مرجع داخلی نتیجه: {result_id}"
                        ),
                    }
                ]
            ),
            "results": results,
        }

    if trace is not None:
        trace.stage("composing", "در حال آماده‌سازی پاسخ")
    try:
        blocks = await _compose(
            question,
            ctx,
            results,
            plan["assumption"],
            crm_results,
            trace,
        )

        blocks = validate_blocks(blocks)

    except Exception as exc:
        return _error(
            f"خطا در آماده‌سازی پاسخ: {exc}",
            results,
        )

    if not blocks:
        return _error(
            "پاسخ مناسبی برای این سؤال تولید نشد.",
            results,
        )

    state = dict(plan["state"])

    if plan["intent"]:
        state["intent"] = plan["intent"]

    state["active_result_ids"] = list(results.keys())

    ctx.update_state(state)
    ctx.record_turn(
        question,
        answer_preview(blocks),
    )

    if trace is not None:
        trace.stage("done", "پاسخ آماده شد")
        trace.state(dict(ctx.state))

    return {
        "blocks": blocks,
        "results": results,
        "trace": trace.dump() if trace is not None else [],
    }


async def _answer_without_llm() -> dict[str, Any]:
    return _error(
        "دستیار هنوز برای پاسخ‌گویی به این سؤال پیکربندی نشده است."
    )


# ---------------------------------------------------------------------------
# Streaming answer (SSE)
#
# The narrative text is streamed token-by-token so the UI can render it as it
# arrives instead of making the user stare at a spinner. Structured blocks
# (charts/tables/metrics) are produced in a second, small LLM call and sent at
# the end as a single "blocks" event.
# ---------------------------------------------------------------------------
async def _llm_stream(
    system: str,
    user: str,
    temperature: float = 0.0,
) -> Any:
    """Yield content deltas from a streaming LLM chat completion.

    Uses the ASYNC OpenAI client: the sync client's ``for chunk in stream``
    blocks the event loop for the whole response (each token waits on a
    blocking socket read), which freezes every other request — including the
    SSE stream itself and /api/health.
    """
    if not settings.has_key:
        raise RuntimeError("LLM is not configured")
    client = AsyncOpenAI(
        api_key=settings.api_key,
        base_url=settings.resolved_base_url,
    )
    try:
        stream = await client.chat.completions.create(
            model=settings.resolved_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
            stream=True,
        )
        async for chunk in stream:
            if not getattr(chunk, "choices", None):
                continue
            delta = chunk.choices[0].delta
            if delta and getattr(delta, "content", None):
                yield delta.content
    finally:
        await client.close()


def _serialize_results(results: dict[str, SqlResult]) -> dict[str, Any]:
    return {
        k: (v.model_dump() if hasattr(v, "model_dump") else v)
        for k, v in results.items()
    }


def _narrative_prompt(
    question: str,
    ctx: SessionState,
    results: dict[str, SqlResult],
    assumption: str,
    crm_results: dict[str, Any] | None = None,
) -> str:
    context = ctx.render_context(question, active_ids=[])
    samples = ctx.result_samples(list(results.keys()))
    crm_block = _render_crm(crm_results or {})
    return f"""
User question:
{question}

Conversation context:
{context}

Assumption:
{assumption or "none"}

Results:
{samples}

Deterministic customer intelligence (backend-computed; do NOT recalculate or
invent — use these values verbatim for any recommendation):
{crm_block or "(none)"}

Answer the user's question using these results, as plain natural-language text.
Do NOT return JSON.
"""


def _blocks_prompt(
    question: str,
    ctx: SessionState,
    results: dict[str, SqlResult],
    assumption: str,
    crm_results: dict[str, Any] | None = None,
) -> str:
    context = ctx.render_context(question, active_ids=[])
    samples = ctx.result_samples(list(results.keys()))
    crm_block = _render_crm(crm_results or {})
    return f"""
User question:
{question}

Conversation context:
{context}

Assumption:
{assumption or "none"}

Results:
{samples}

Deterministic customer intelligence (backend-computed):
{crm_block or "(none)"}

Return ONLY a JSON array of blocks (non-markdown). Use only the available
resultIds. Return an empty array if no block genuinely improves the answer.
"""


async def _compose_text_stream(
    question: str,
    ctx: SessionState,
    results: dict[str, SqlResult] | None = None,
    assumption: str = "",
    crm_results: dict[str, Any] | None = None,
    trace: Trace | None = None,
) -> Any:
    """Stream the natural-language narrative answer as text deltas."""
    if results or crm_results:
        system = NARRATIVE_SYSTEM
        user = _narrative_prompt(question, ctx, results or {}, assumption, crm_results)
        temperature = 0.2
    else:
        system = CHAT_SYSTEM
        user = ctx.render_context(question)
        temperature = 0.4
    t0 = time.monotonic()
    out = ""
    async for delta in _llm_stream(system, user, temperature):
        out += delta
        yield delta
    if trace is not None:
        trace.llm(
            call="narrative", model=settings.resolved_model,
            input_chars=len(system) + len(user), output_chars=len(out),
            latency_ms=int((time.monotonic() - t0) * 1000),
        )


async def _compose_blocks(
    question: str,
    ctx: SessionState,
    results: dict[str, SqlResult],
    assumption: str,
    crm_results: dict[str, Any] | None = None,
    trace: Trace | None = None,
) -> list[dict]:
    """Produce optional structured blocks (charts/tables/metrics) at the end."""
    if not results:
        return []
    raw = await _llm_call_async(
        _blocks_system(", ".join(results.keys())),
        _blocks_prompt(question, ctx, results, assumption, crm_results),
        temperature=0.0,
        trace=trace,
        call="blocks",
    )
    parsed = contracts.parse_blocks_json(raw)
    if isinstance(parsed, list):
        return [b for b in parsed if b.get("type") != "markdown"]
    return []


async def _database_answer_stream(
    question: str,
    ctx: SessionState,
    trace: Trace | None = None,
) -> Any:
    """Yield SSE-style event dicts for the full database-backed answer."""
    if trace is not None:
        trace.meta(session_id=ctx.session_id, question=question)
        trace.stage("planning", "شروع تحلیل سؤال")
        for ev in trace.drain():
            yield {"type": ev["t"], **{k: v for k, v in ev.items() if k not in ("t", "ts")}}
    yield {"type": "status", "status": "planning"}

    plan = None
    try:
        async for item in _plan_stream(question, ctx, trace):
            kind, payload = item
            if kind == "thinking":
                yield {"type": "thinking", "text": payload}
            else:
                plan = payload
    except Exception as exc:  # noqa: BLE001
        reason = str(exc).strip() or "نتیجه برنامه‌ریزی نامعتبر بود"
        yield {"type": "error", "message": f"خطا در تحلیل سؤال: {reason}"}
        return

    if trace is not None:
        for ev in trace.drain():
            yield {"type": ev["t"], **{k: v for k, v in ev.items() if k not in ("t", "ts")}}

    if plan is None:
        yield {"type": "error", "message": "خطا در تحلیل سؤال: طرح تولید نشد."}
        return

    steps = plan["steps"]

    # No tools needed -> plain conversational answer (streamed text only).
    if not steps:
        yield {"type": "status", "status": "composing"}
        try:
            async for delta in _compose_text_stream(question, ctx, trace=trace):
                yield {"type": "text", "text": delta}
        except Exception as exc:  # noqa: BLE001
            reason = str(exc).strip() or "پاسخ نامعتبر بود"
            yield {"type": "error", "message": f"خطا در آماده‌سازی پاسخ: {reason}"}
            return
        if trace is not None:
            for ev in trace.drain():
                yield {"type": ev["t"], **{k: v for k, v in ev.items() if k not in ("t", "ts")}}
        yield {"type": "blocks", "blocks": [], "results": {}}
        return

    results: dict[str, SqlResult] = {}
    crm_results: dict[str, Any] = {}
    last_sql: str | None = None

    yield {"type": "status", "status": "querying"}

    # Multi-step requests: let the customer know it will take a moment.
    if len(steps) > 1:
        yield {
            "type": "thinking",
            "text": "این سؤال چند بخش دارد؛ در حال بررسی آن در چند مرحله هستم…",
        }

    for step in steps:
        kind = step["kind"]

        if kind == "reuse":
            result_id = step["resultId"]
            if not result_id:
                yield {"type": "error", "message": "نتیجه قبلی مشخص نشد."}
                return
            result = ctx.get_result(result_id)
            if result is None:
                yield {
                    "type": "error",
                    "message": "اطلاعات موردنیاز از نتیجه قبلی دیگر در دسترس نیست.",
                }
                return
            results[result_id] = result

        elif kind == "query":
            sql = (step["sql"] or "").strip()
            if not sql:
                yield {"type": "error", "message": "برای این سؤال اطلاعاتی برای جستجو تولید نشد."}
                return

            normalized = sql.lstrip().lower()
            if not normalized.startswith(("select", "with")):
                yield {"type": "error", "message": "کوئری تولیدشده مجاز نیست."}
                return

            if trace is not None:
                trace.stage("query", "در حال اجرای پرس‌وجو", sql[:200])
                for ev in trace.drain():
                    yield {"type": ev["t"], **{k: v for k, v in ev.items() if k not in ("t", "ts")}}
            yield {"type": "thinking", "text": f"در حال اجرای پرس‌وجو: {sql}"}

            try:
                data = await _exec_query(question, sql, trace)
            except Exception as exc:  # noqa: BLE001
                yield {"type": "error", "message": f"خطا در دریافت اطلاعات: {exc}"}
                return

            if data.get("error"):
                yield {"type": "error", "message": f"خطا در دریافت اطلاعات: {data['error']}"}
                return

            result_id = data.get("resultId") or "r1"
            results[result_id] = ctx.add_result(
                result_id,
                step.get("purpose") or "",
                data.get("columns", []),
                data.get("rows", []),
                data.get("n_rows"),
            )
            last_sql = sql
            if trace is not None:
                trace.result(result_id, step.get("purpose") or "",
                             data.get("columns", []), data.get("n_rows", 0))
                for ev in trace.drain():
                    yield {"type": ev["t"], **{k: v for k, v in ev.items() if k not in ("t", "ts")}}

        elif kind == "crm":
            tool = step.get("tool") or ""
            customer_id = step.get("customer_id") or ""
            if tool not in CRM_TOOLS:
                yield {"type": "error", "message": "درخواست سیگنال/اقدام مشتری نامعتبر است."}
                return
            if tool == "top_at_risk_customers":
                crm_args: dict[str, Any] = {"limit": int(step.get("limit") or 10)}
            elif not customer_id:
                yield {"type": "error", "message": "درخواست سیگنال/اقدام مشتری نامعتبر است."}
                return
            else:
                crm_args = {"customer_id": customer_id}
            if trace is not None:
                trace.stage("crm_tool", f"در حال دریافت نتایج {tool}",
                            customer_id or str(crm_args))
                for ev in trace.drain():
                    yield {"type": ev["t"], **{k: v for k, v in ev.items() if k not in ("t", "ts")}}
            try:
                data = await _call_crm_tool(await _ensure_mcp(), tool, crm_args, trace)
            except Exception as exc:  # noqa: BLE001
                yield {"type": "error", "message": f"خطا در دریافت اطلاعات مشتری: {exc}"}
                return
            crm_results[f"{tool}:{customer_id or crm_args.get('limit')}"] = data
            if trace is not None:
                for ev in trace.drain():
                    yield {"type": ev["t"], **{k: v for k, v in ev.items() if k not in ("t", "ts")}}

        else:
            yield {"type": "error", "message": "نوع درخواست قابل تشخیص نیست."}
            return

    huge = next(
        (
            (result_id, result.n_rows)
            for result_id, result in results.items()
            if is_huge(result.n_rows)
        ),
        None,
    )

    if huge:
        result_id, count = huge
        content = too_huge_message(count) + "\n\n" + f"مرجع داخلی نتیجه: {result_id}"
        yield {"type": "text", "text": content}
        yield {
            "type": "blocks",
            "blocks": [],
            "results": _serialize_results(results),
        }
        return

    # Stream the narrative answer text.
    if trace is not None:
        trace.stage("composing", "در حال آماده‌سازی پاسخ")
        for ev in trace.drain():
            yield {"type": ev["t"], **{k: v for k, v in ev.items() if k not in ("t", "ts")}}
    yield {"type": "status", "status": "composing"}
    narrative = ""
    try:
        async for delta in _compose_text_stream(question, ctx, results, plan["assumption"], crm_results, trace):
            narrative += delta
            yield {"type": "text", "text": delta}
    except Exception as exc:  # noqa: BLE001
        yield {"type": "error", "message": f"خطا در آماده‌سازی پاسخ: {exc}"}
        return
    if trace is not None:
        for ev in trace.drain():
            yield {"type": ev["t"], **{k: v for k, v in ev.items() if k not in ("t", "ts")}}

    # Structured blocks (charts/tables/metrics) appended after the text.
    yield {"type": "thinking", "text": "در حال آماده‌سازی نمودار و جدول…"}
    try:
        blocks = await _compose_blocks(question, ctx, results, plan["assumption"], crm_results, trace)
    except Exception:  # noqa: BLE001 - blocks are optional
        blocks = []
    if trace is not None:
        for ev in trace.drain():
            yield {"type": ev["t"], **{k: v for k, v in ev.items() if k not in ("t", "ts")}}

    blocks = validate_blocks(blocks)

    state = dict(plan["state"])
    if plan["intent"]:
        state["intent"] = plan["intent"]
    state["active_result_ids"] = list(results.keys())

    ctx.update_state(state)
    ctx.record_turn(
        question,
        answer_preview(
            [{"id": "b0", "type": "markdown", "content": narrative or "(پاسخ)"}]
            + [b.model_dump() if hasattr(b, "model_dump") else b for b in blocks]
        ),
    )

    if trace is not None:
        trace.stage("done", "پاسخ آماده شد")
        trace.state(dict(ctx.state))
        for ev in trace.drain():
            yield {"type": ev["t"], **{k: v for k, v in ev.items() if k not in ("t", "ts")}}

    yield {
        "type": "blocks",
        "blocks": [b.model_dump() if hasattr(b, "model_dump") else b for b in blocks],
        "results": _serialize_results(results),
        "query": last_sql,
    }


async def answer_stream(
    question: str,
    history: list[dict] | None = None,
    session_id: str | None = None,
    debug: bool = False,
) -> Any:
    """Async generator yielding event dicts for the streaming chat endpoint.

    With ``debug=True`` the events include raw LLM outputs (planner/composer
    JSON); otherwise only sizes/latency are reported. Stage/plan/tool/result/
    state events are always emitted so the UI can show how the answer is built.
    """
    if not settings.has_key:
        yield {"type": "error", "message": "دستیار هنوز برای پاسخ‌گویی به این سؤال پیکربندی نشده است."}
        return

    ctx = _get_session(session_id or "_")
    trace = Trace(debug=debug)

    try:
        async for event in _database_answer_stream(question, ctx, trace):
            yield event
        yield {"type": "done"}
    except Exception as exc:  # noqa: BLE001
        # Hard failure: drop the cached MCP session so the next request
        # restarts it cleanly instead of reusing a broken connection.
        await close_mcp()
        yield {"type": "error", "message": f"در پاسخ‌گویی مشکلی پیش آمد: {exc}"}
        yield {"type": "done"}


async def answer(
    question: str,
    history: list[dict] | None = None,
    session_id: str | None = None,
    session_state: SessionState | None = None,
    debug: bool = False,
) -> dict[str, Any]:

    if not settings.has_key:
        return await _answer_without_llm()

    ctx = session_state

    if ctx is None:
        ctx = _get_session(
            session_id or "_"
        )

    trace = Trace(debug=debug)

    try:
        return await _database_answer(
            question,
            ctx,
            trace,
        )

    except Exception as exc:
        # If the MCP server died, drop the cached session so the next request
        # restarts it cleanly instead of reusing a broken connection.
        await close_mcp()
        return _error(
            f"در پاسخ‌گویی مشکلی پیش آمد: {exc}"
        )