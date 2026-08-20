# Customer 360 Database + Copilot Backend

This repo now includes a **DuckDB database** holding each raw data sheet as its
own table, a **DuckDB MCP server**, and a **FastAPI backend** that lets the
frontend copilot answer questions with live database queries.

## Database

`data/processed/customer_360.duckdb` — one table per sheet in `data/raw/DATASET.xlsx`:

| Table | Sheet |
|---|---|
| `customers` | مشتریان |
| `products` | محصولات |
| `invoices` | فاکتورها |
| `sales` | فروش |
| `realized_costs` | اجزای_هزینه_تحقق |
| `collections` | وصول |
| `complaints` | شکایات |
| `complaint_links` | اتصال_شکایت |
| `crm_interactions` | تعاملات_CRM |
| `dev_requests` | درخواست_توسعه |
| `quality_labs` | کیفیت_لات |
| `hembaft_lots` | همبافت_لات |
| `offers` | آفرها |
| `wallet_share` | سهم_سبد |
| `market_signals` | سیگنال_بازار |
| `monthly_costs` | برآورد_هزینه_ماهانه |
| `_meta` | table purpose / PK notes |

Rebuild it any time with `python scripts/build_db.py`.

## MCP server

`backend/mcp/duckdb_server.py` exposes the DB as MCP tools over stdio:

- `query(sql, max_rows)` — **primary analytical tool**: read-only SELECT /
  WITH ... SELECT; returns `{resultId, columns, rows, n_rows, truncated,
  returned_rows}`. resultId is generated **server-side**; the DB connection is
  opened read-only and writes/external access are blocked.
- `run_sql(...)` — alias of `query` for backward compatibility.
- `list_tables()` / `get_schema(table)` — **fallback only** (schema discovery).

The LLM gets a **compact static Customer360 schema + relationships**
(`backend/mcp/schema_context.py`) embedded in its prompt, so it answers most
business questions with **one `query` call** instead of discovering the schema
each time. DuckDB-specific SQL notes (dates stored as TEXT → `CAST(x AS DATE)`,
`strftime` not `to_char`) are included to reduce failed queries; a failed query
is retried once with the DB error fed back to the LLM.

Run standalone: `python -m backend.mcp.duckdb_server`

## Backend API

`backend/main.py` (FastAPI) — the frontend calls it:

- `GET  /api/health`
- `GET  /api/dashboard`        → live KPIs + purchase/complaint trends + segment/status distributions
- `GET  /api/customers`        → real customer list with aggregated orders/revenue/complaints
- `GET  /api/customers/{id}/360` → real Customer-360 (sales, complaints, collections, risk)
- `POST /api/chat`  `{ "question": "...", "history": [...], "session_id": "..." }` → `{ blocks, results }`

The read endpoints (`backend/api_data.py`) query the DuckDB directly (read-only)
so the Dashboard, Customers list, and Customer-360 render **real data — no mock
data**. The agent plans read-only SQL (using the static schema in context), runs
it via the MCP `query` tool (each result gets a server-generated `resultId`),
and composes an **ordered list of Blocks** — the strict UI contract shared with
the frontend.

### Bounded agent context (token efficiency)

To keep the LLM context small and predictable, the agent keeps exact database
results **out** of the conversation history (`backend/agents/context.py`):

- **ResultStore**: exact MCP results live in a per-session store keyed by the
  server-generated `resultId`, never inside history/state. Capped to
  `MAX_STORED_RESULTS` (oldest evicted).
- **History/state** only carry lightweight data: a compact summary of older
  turns (max `MAX_LOG_ENTRIES` `{q, a}` pairs), the last `MAX_RECENT_MESSAGES`
  full messages, a small structured analytical state (selected customer/product/
  order, date range, filters, intent, active resultIds), and per-result metadata
  (`resultId`, `purpose`, `columns`, `n_rows`).
- The LLM is shown at most a tiny row sample (`MAX_SAMPLE_ROWS`) — never the full
  grids — and the whole rendered context is capped (`MAX_CONTEXT_CHARS`).
- **Result reuse**: follow-ups can reference an existing `resultId` (`kind: reuse`)
  instead of re-querying the database.
- The frontend sends a stable `session_id` (regenerated on "new chat"); the
  backend holds per-session state in a bounded in-memory store (`MAX_SESSIONS`).

`tests/test_agent_context.py` proves context size stays bounded as conversations
and DB results grow, and that follow-ups reuse existing resultIds without
re-querying.

### Speed & token optimization

The agent is tuned for minimal latency, tokens and tool calls:

- **Short pipeline**: exactly one LLM *planning* step, then (for data) exactly
  one LLM *composition* step — no per-turn intent classifier, no schema
  discovery, no deterministic post-processing.
- **Tool-calling planner contract**: the planner returns a `steps` array
  (`{"tool": "query" | "reuse", "input": {...}}`); empty `steps` means a plain
  conversational answer. The agent executes the steps in order and composes a
  single reply over all results.
- **Structured JSON contracts** (`backend/agents/contracts.py`): plans and blocks
  are validated with pydantic (JSON Schema) instead of regex extraction, so the
  LLM is steered to strict JSON and parsing never silently mis-fires.
- **One SQL query by default**: the plan prompt prefers a single read-only query
  and caps new queries (`MAX_QUERIES`); reuse steps never count against it.
  DuckDB does filtering/aggregation/calculation/sort/limit — the LLM only
  interprets results.
- **Lean per-step system prompts**: the full schema is sent only on the planning
  step (needed to write SQL); the composition and conversational steps use much
  smaller prompts, cutting ~1.6k prompt chars per data request.
- **Explicit failures**: plan/compose/DB failures surface an explicit message
  instead of silently re-running the LLM or falling back to a generic reply.
- **Bounded context + ResultStore** (above) keep exact DB results out of the LLM
  context, and resultIds are reused across turns.

Benchmark (`scripts/benchmark_agent.py`) against the live backend shows every
request uses exactly **2 LLM calls** (plan + compose) and **1 SQL (MCP) call**
for data questions (0 for chat), with small, bounded prompt sizes:

```
request        latency  LLM  SQL   ~tok  blocks
count            14.7s    2    1   2491  markdown,metric,markdown
top_customers    54.5s    2    1   2570  markdown,table,markdown
sales_trend      76.3s    2    1   2621  markdown,chart,table,markdown
complaints       44.5s    2    1   2539  markdown,table,markdown
```

Latency is dominated by DeepSeek round-trips (high variance between runs); the
call/token counts are the stable, bounded part the design guarantees.

### Block response contract

An assistant reply is an ordered array of blocks plus a `results` map keyed by
`resultId`:

```json
{
  "blocks": [
    {"id": "b1", "type": "markdown", "content": "## تحلیل فروش ..."},
    {"id": "b2", "type": "metric", "resultId": "r1", "label": "رشد فروش", "valueKey": "growth"},
    {"id": "b3", "type": "chart", "resultId": "r1", "chartType": "line", "xKey": "month",
     "series": [{"dataKey": "sales", "label": "فروش"}]}
  ],
  "results": {"r1": {"columns": ["month", "sales"], "rows": [...], "n_rows": 8}}
}
```

Supported block types: `markdown`, `metric`, `chart`, `histogram`, `table`,
`recommendation`, `customer_card`, `product_card`, `order_card`.

The order of the array is the exact visual order in the chat. Structured blocks
**reference** MCP results by `resultId` — the LLM never copies large data into
Markdown. Business rules are enforced (actual cost over estimated, `COUNT(DISTINCT
order_id)` for orders vs `SUM(quantity)` for units, latest CRM version, as-of
semantics). Huge results (>1000 rows) are not analysed inline; the copilot tells
the user the data is too large.

### Always-respond & assumption handling

- There is **no separate DB-intent classifier** — every question goes straight to
  the LLM, which decides (via the system prompt) whether to plan queries or just
  chat. No keyword heuristics or deterministic block post-processing.
- The copilot **always produces an output**: LLM calls retry on transient
  failures, and if block composition returns nothing usable, it falls back to a
  plain conversational answer.
- When a question is ambiguous ("an arbitrary customer", "some product"), the
  agent picks a sensible concrete default (e.g. the most profitable customer),
  **states the assumption** in the first markdown block, shows the results for
  it, and ends with a markdown block explaining how the answer would change for
  a different choice.

### Run it

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r backend/requirements.txt
./scripts/run_backend.sh
# or: uvicorn backend.main:app --reload --port 8000
```

## LLM configuration

Copy `.env.example` to `.env` and set `LLM_API_KEY`. Supports:

- **OpenAI**: `LLM_PROVIDER=openai`, `LLM_API_KEY=sk-...`
- **DeepSeek**: `LLM_PROVIDER=deepseek`, `LLM_API_KEY=sk-...`
- **Any OpenAI-compatible / local**: `LLM_PROVIDER=custom`, `LLM_BASE_URL=...`

Without a key, the copilot still works but returns schema-only answers.

## Frontend

`frontend/vite.config.ts` proxies `/api` → `http://127.0.0.1:8000`. The frontend
is **fully Persian (fa) and RTL** (`lang="fa" dir="rtl"`, Vazirmatn font) and
renders **live data from the backend** — the mock-data layer has been removed.
The copilot tries the live backend first and, if it is offline, shows an honest
message.

```bash
cd frontend && npm install && npm run dev
```

## Tests

```bash
# backend (pytest)
pip install pytest pytest-asyncio
python -m pytest tests/ -q

# frontend (vitest)
cd frontend && npx vitest run
```

Tests cover Block schema validation & ordering, arbitrary block order, resultId
resolution, huge-result handling, order-count vs quantity distinction, and the
MCP query tool (server-side resultId, read-only enforcement, truncation,
single-query business answers, failed-query retry).

## End-to-end (Playwright)

Playwright drives the real frontend chatbot against the live backend. Both
servers must be running first:

```bash
./scripts/run_backend.sh                 # FastAPI on :8000
cd frontend && npm run dev               # Vite on :5173
```

Then run the E2E suite:

```bash
cd e2e
npm install                 # first time (installs @playwright/test)
npx playwright install chromium   # first time (downloads browser)
npx playwright test         # headless
npx playwright test --headed  # watch the browser
```

`e2e/tests/copilot.spec.mjs` opens the copilot, sends a greeting, requests a
chart ("monthly sales trend"), and asserts a real chart renders (no generic
error). It also verifies **multi-step chat** (a follow-up keeps context and
returns a customer card). These hit the live DeepSeek API, so they take ~1-2 min.

## Copilot behaviour

- The live backend always responds; if it is unreachable the copilot says so
  honestly instead of showing canned mock text.
- The LLM agent **always answers in Persian** regardless of input language, and
  the whole UI is RTL.
- Data answers include **1-2 non-text blocks** (chart when it fits the intent,
  plus a **customer/product card or table** whenever the user asks about
  customers, products, or orders).
- Multi-step questions reuse prior context (e.g. "that customer" refers back).
