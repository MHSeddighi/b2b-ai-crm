# 1. هدف محصول

ساخت سیستمی که داده‌های پراکنده هر مشتری را به یک تصمیم قابل اقدام برای مدیر فروش تبدیل کند.

مسیر اصلی محصول:

**Data → Current State → Signals → Customer Status → Recommended Action → Evidence**

سیستم نباید فقط بگوید چه اتفاقی افتاده؛ باید بگوید:

1. چه چیزی تغییر کرده؟
2. وضعیت فعلی چیست؟
3. چرا مهم است؟
4. چه کاری باید انجام شود؟
5. این نتیجه بر اساس چه داده‌ای است؟

---

# 2. کاربر اصلی

**Sales Manager / Account Manager**

کاربر باید بتواند در کمتر از چند دقیقه بفهمد:

- کدام مشتری نیاز به توجه دارد؟
- مشکل یا فرصت چیست؟
- آیا مشکل هنوز وجود دارد یا حل شده؟
- مشتری ارزش پیگیری دارد یا نه؟
- الان چه اقدامی باید انجام شود؟

---

# 3. خروجی نهایی هر مشتری

برای هر مشتری سیستم باید یک Object نهایی شبیه این تولید کند:

```json
{
  "customer_id": "CUST-058",
  "status": "Needs Attention",
  "priority": "High",

  "summary": "مشتری ارزشمند است اما خرید در حال کاهش است و اخیراً مشکل کیفیت داشته.",

  "signals": [],
  "recommended_actions": [],
  "evidence": [],
  "confidence": "High"
}
```

---

# 4. تقسیم پروژه

پروژه به 7 ماژول مستقل تقسیم شود:

1. Data & Tool Layer
2. Customer 360
3. Current State Engine
4. Signal Engine
5. Customer Classification
6. Action Engine
7. AI Explanation & Evidence

هر بخش می‌تواند Owner جدا داشته باشد.

---

# MODULE 1 — Data & Tool Layer

## مسئولیت

فرد مسئول این بخش باید تمام Data Sourceها را برای سیستم قابل استفاده کند.

## کارهایی که باید انجام شود

برای هر جدول مشخص شود:

- نام جدول
- کاربرد جدول
- Grain جدول
- Primary Key
- Foreign Keys
- Entityها
- معنی ستون‌ها
- ارتباط با جدول‌های دیگر
- محدودیت‌ها و مشکلات Data Quality
- چه سؤال‌هایی با این جدول قابل پاسخ است

مثلاً:

### فروش

کاربرد:

> فهمیدن اینکه مشتری چه چیزی، چه زمانی، با چه مقدار و چه قیمتی خریده است.

Tool احتمالی:

```text
get_customer_sales(
    customer_id,
    start_date,
    end_date,
    product_id
)
```

خروجی باید Structured باشد.

## Toolهای مورد نیاز

حداقل:

```text
get_customer_profile()
get_customer_sales()
get_customer_invoices()
get_customer_payments()
get_customer_complaints()
get_customer_crm_interactions()
get_customer_offers()
get_customer_wallet_share()
get_customer_development_requests()
get_customer_quality_records()
get_customer_costs()
```

## نکته مهم

LLM نباید مستقیماً SQL آزاد روی تمام دیتابیس بزند.

Toolها بهتر است کنترل‌شده و قابل پیش‌بینی باشند.

## Definition of Done

این بخش تمام شده است اگر:

- برای یک Customer\_ID بتوان تمام داده‌های مرتبط را بازیابی کرد.
- Duplicate Join ایجاد نشود.
- Customer Identity Mapping حل شده باشد.
- هر خروجی Source و Timestamp داشته باشد.

---

# MODULE 2 — Customer 360

## مسئولیت

تبدیل داده‌های مختلف به یک View واحد از مشتری.

## خروجی مورد انتظار

```json
{
  "customer": {},
  "sales": {},
  "payments": {},
  "profitability": {},
  "complaints": {},
  "relationship": {},
  "offers": {},
  "wallet": {},
  "opportunities": {},
  "recent_events": []
}
```

## صفحه UI پیشنهادی

بالای صفحه:

**Customer Name**

سپس:

```text
Current Status
Priority
Real Profit
Purchase Trend
Payment Status
Wallet Share
Relationship Status
```

پایین‌تر:

### Recent Events

مثلاً:

```text
12 Aug — Payment received
8 Aug — CRM meeting
2 Aug — Complaint closed
26 Jul — Order placed
```

## نکته

Customer 360 نباید فقط چند جدول کنار هم باشد.

باید یک **Current Account View** ایجاد کند.

## Definition of Done

با یک API Call:

```text
GET /customer/{id}/360
```

باید View کامل مشتری برگردد.

---

# MODULE 3 — Current State Engine

این بخش بسیار مهم است.

## مسئولیت

تشخیص اینکه یک Event قدیمی هنوز مهم است یا نه.

مثلاً:

```text
Complaint happened
```

کافی نیست.

باید بفهمیم:

```text
Complaint happened
↓
Was it resolved?
↓
Did it repeat?
↓
Did later purchases recover?
↓
Is it still relevant today?
```

## Stateهای پیشنهادی

برای Issueها:

```text
NEW
ACTIVE
IMPROVING
RESOLVED
RECURRING
STALE
```

## مثال Complaint

ورودی:

- Complaint Severity
- Complaint Date
- Resolution
- Lot Quality
- Recent Orders
- New Complaints

خروجی:

```json
{
  "issue": "Quality",
  "state": "RESOLVED",
  "severity": "High",
  "current_relevance": "Low",
  "reason": "شکایت بسته شده و دو خرید بعدی بدون شکایت بوده‌اند."
}
```

## برای چه چیزهایی State بسازیم؟

### Quality

- مشکل هنوز وجود دارد؟
- رفع شده؟
- تکرار شده؟

### Payment

- هنوز بدهکار است؟
- پرداخت کرده؟
- رفتار پرداخت بهتر شده؟

### Purchase Decline

- کاهش ادامه دارد؟
- خرید برگشته؟
- فصلی بوده؟

### Relationship

- رابطه اخیراً بهتر یا بدتر شده؟

### Offer

- Offer هنوز Open است؟
- Accepted؟
- Rejected؟
- Expired؟

## Definition of Done

هر Problem Signal باید علاوه بر History دارای **Current State** باشد.

---

# MODULE 4 — Signal Engine

## مسئولیت

محاسبه Signalها با Code.

LLM نباید Signal اصلی را محاسبه کند.

## Signalهای MVP

### 1. RFM

خروجی:

```text
R
F
M
Previous RFM
Current RFM
Movement
```

مهم‌تر از Score:

```text
5-5-5 → 3-4-5
```

---

### 2. LTV

خروجی:

```text
Estimated Future Value
Confidence
Assumptions
```

برای MVP می‌تواند Formula-based باشد.

---

### 3. Share of Wallet

```text
Our Spend / Estimated Customer Spend
```

خروجی:

```text
Current Wallet Share
Previous Wallet Share
Change
Confidence
Source
```

---

### 4. Real Profit

حداقل:

```text
Revenue
- COGS
- Returns
- Cost of Money
= Real Profit
```

هم Amount و هم Margin نمایش داده شود.

---

### 5. Payment Behaviour

موارد مهم:

```text
Average Delay
Outstanding Balance
Returned Cheques
Trend
```

خروجی مثلاً:

```text
GOOD
WATCH
BAD
```

---

### 6. Relationship Quality

ورودی:

- CRM interactions
- complaints
- offer acceptance
- interaction recency
- unresolved issues

خروجی:

```text
STRONG
NORMAL
WEAKENING
POOR
```

---

### 7. Purchase Trend

مقایسه رفتار مشتری با History خودش.

خروجی:

```text
GROWING
STABLE
DECLINING
RECOVERING
ABNORMAL_DROP
```

---

### 8. Churn Risk

ترکیبی از Signalهای دیگر.

مثلاً:

```text
Purchase Decline
+ Relationship Decline
+ Complaint
+ Offer Rejection
+ Interaction Gap
```

خروجی:

```text
LOW
MEDIUM
HIGH
```

همراه با Reason Codes.

---

### 9. Cross-sell Opportunity

بررسی:

- Product Mix
- Wallet Gap
- Similar Customers
- Development Requests
- Offers
- Profitability
- Payment Behaviour

خروجی:

```json
{
  "product": "Product X",
  "opportunity": "HIGH",
  "reason": "...",
  "blocked_by": []
}
```

## Definition of Done

برای هر مشتری API زیر وجود داشته باشد:

```text
GET /customer/{id}/signals
```

و هر Signal شامل این‌ها باشد:

```text
value
status
trend
reason_codes
evidence_ids
calculated_at
```

---

# MODULE 5 — Customer Classification

هدف این بخش ساده‌کردن 9 Signal برای مدیر فروش است.

به‌جای اصطلاحات پیچیده، پیشنهاد می‌شود فقط 4 وضعیت داشته باشیم.

## 1. رشد بده

مشتری خوب است و ظرفیت رشد دارد.

مثلاً:

```text
Real Profit HIGH
Wallet Share LOW
Payment GOOD
Relationship GOOD
```

→ **رشد بده**

---

## 2. حفظ کن

مشتری ارزشمند است ولی باید مراقب او باشیم.

```text
High Value
High Profit
High Wallet Share
```

→ **حفظ کن**

---

## 3. مشکل را حل کن

مشتری ارزش دارد اما چیزی جلوی رشد را گرفته.

مثلاً:

```text
High Value
Purchase ↓
Complaint Active
```

یا:

```text
Sales High
Payment Bad
Real Profit Low
```

→ **مشکل را حل کن**

---

## 4. کمتر وقت بگذار

```text
Low Profit
Low Potential
Low Wallet Opportunity
High Cost to Serve
```

→ **کمتر وقت بگذار**

## Definition of Done

هر مشتری دقیقاً یک **Primary State** داشته باشد و سیستم توضیح دهد چرا.

---

# MODULE 6 — Action Engine

## مسئولیت

تبدیل وضعیت مشتری به Action مشخص.

Actionها باید محدود و قابل کنترل باشند.

## Action Catalog

### Relationship

```text
CALL_CUSTOMER
SCHEDULE_MEETING
CHECK_SATISFACTION
ESCALATE_ACCOUNT
```

### Quality

```text
FOLLOW_UP_COMPLAINT
QUALITY_REVIEW_MEETING
SEND_QUALITY_REPORT
```

### Sales

```text
CROSS_SELL_PRODUCT
UPSELL_PRODUCT
SEND_OFFER
RENEW_OFFER
```

### Commercial

```text
RENEGOTIATE_PRICE
RENEGOTIATE_PAYMENT_TERMS
REDUCE_DISCOUNT
```

### Collection

```text
FOLLOW_UP_PAYMENT
REVIEW_CREDIT_LIMIT
BLOCK_NEW_CREDIT_OFFER
```

### Attention

```text
INCREASE_ATTENTION
MAINTAIN_ATTENTION
REDUCE_ATTENTION
```

---

# Action Rules

مثلاً:

```text
IF
Churn Risk = HIGH
AND LTV = HIGH
AND Complaint State = ACTIVE

THEN
QUALITY_REVIEW_MEETING
```

---

```text
IF
Wallet Share = LOW
AND Real Profit = HIGH
AND Payment = GOOD
AND Relationship != POOR

THEN
CROSS_SELL_PRODUCT
```

---

```text
IF
Cross Sell = HIGH
BUT Payment = BAD

THEN
FOLLOW_UP_PAYMENT

NOT
SEND_OFFER
```

این قسمت بسیار مهم است:

**Opportunity ≠ Action**

Constraintها باید قبل از Action بررسی شوند.

---

# Action Object

```json
{
  "action": "SCHEDULE_MEETING",
  "priority": "HIGH",
  "owner": "Account Manager",
  "reason_codes": [
    "PURCHASE_DECLINE",
    "ACTIVE_QUALITY_ISSUE",
    "HIGH_LTV"
  ],
  "objective": "رفع مشکل کیفیت و بازیابی حجم خرید"
}
```

---

# MODULE 7 — AI Explanation & Evidence Layer

## مسئولیت LLM

LLM قرار نیست تصمیم مالی محاسبه کند.

وظایفش:

### 1. خلاصه کردن Customer 360

مثلاً:

> مشتری همچنان سودآور است، اما خرید سه ماه اخیر ۲۸٪ کاهش یافته است.

### 2. خواندن متن CRM و Complaint

استخراج:

```text
Problem
Cause
Sentiment
Commitment
Next step
```

### 3. توضیح Signalها

### 4. توضیح Action

مثلاً:

> جلسه بررسی کیفیت پیشنهاد شده زیرا افت خرید بعد از دو شکایت کیفی شروع شده و آخرین شکایت هنوز باز است. مشتری همچنان LTV بالایی دارد.

---

# Evidence

هر Claim باید Evidence داشته باشد.

مثلاً UI:

**Why this action?**

> Purchase ↓ 28%\
> Quality complaint still active\
> Customer LTV: High\
> Real Profit: 11.8%

**View evidence →**

سپس رکوردهای واقعی باز شوند.

## Definition of Done

LLM نباید عدد جدید اختراع کند.

تمام عددها باید از Signal Engine یا Data Tools وارد Prompt شوند.

---

# 5. Contract بین تمام تیم‌ها

همه Moduleها باید حول یک Customer ID مشترک کار کنند.

Flow:

```text
Customer_ID
    ↓
Customer 360
    ↓
Current States
    ↓
Signals
    ↓
Classification
    ↓
Actions
    ↓
LLM Explanation
    ↓
Evidence
```

---

# 6. چیزی که در UI باید دیده شود

صفحه اصلی می‌تواند لیست مشتریان باشد:

| Customer | وضعیت          | Priority | مشکل/فرصت     | Action           |
| -------- | -------------- | -------- | ------------- | ---------------- |
| A        | رشد بده        | High     | Wallet gap    | Cross-sell       |
| B        | مشکل را حل کن  | High     | Late payment  | Payment meeting  |
| C        | حفظ کن         | Medium   | Stable        | Monitor          |
| D        | کمتر وقت بگذار | Low      | Low potential | Reduce attention |

با کلیک روی مشتری:

## Customer 360

سپس:

### Why now?

سه Signal مهم.

### Current situation

مشکلات Open / Resolved.

### Recommended Action

یک Action اصلی.

### Why?

Evidence.

---

# 7. Demo Scenario پیشنهادی

برای Demo بهتر است یک مشتری انتخاب شود که Story جذابی داشته باشد:

```text
مشتری قبلاً خوب بوده
↓
خرید کاهش یافته
↓
شکایت کیفیت ثبت شده
↓
بررسی Current State
↓
مشکل هنوز Active است
↓
Real Profit همچنان خوب است
↓
LTV بالا است
↓
نباید مشتری را رها کرد
↓
System = "مشکل را حل کن"
↓
Action = جلسه کیفیت
↓
Evidence نمایش داده شود
```

و مشتری دوم:

```text
Wallet Share پایین
+ Profit بالا
+ Payment خوب
+ Relationship خوب
↓
"رشد بده"
↓
Cross-sell Product X
```

با همین دو Case تقریباً تمام ارزش محصول قابل نمایش است.

---

# 8. تقسیم پیشنهادی بین اعضای تیم

## Person 1 — Data

مسئول:

- Metadata
- Relationships
- Identity Resolution
- Database
- Tool Functions

تحویل:

**Customer Data API**

---

## Person 2 — Analytics

مسئول:

- RFM
- Real Profit
- Payment
- Wallet
- Purchase Trend
- LTV

تحویل:

**Signal Engine**

---

## Person 3 — Decision Engine

مسئول:

- Current State
- Churn
- Relationship
- Cross-sell
- Classification
- Action Rules

تحویل:

**Decision API**

---

## Person 4 — AI

مسئول:

- Complaint Extraction
- CRM Text Extraction
- Customer Summary
- Explanation
- Evidence Grounding

تحویل:

**AI Synthesis Layer**

---

## Person 5 — Frontend

مسئول:

- Customer list
- Customer 360
- Signals
- Recommended Action
- Evidence Drill-down

تحویل:

**Demo Application**

اگر اعضای تیم کمتر هستند، Data + Analytics و Decision + AI را ادغام کنید.

---

# 9. قانون اصلی محصول

هیچ Action نباید فقط به دلیل وجود یک Event صادر شود.

همیشه:

```text
Historical Event
+
Current State
+
Customer Value
+
Commercial Context
+
Constraints
=
Action
```

مثلاً:

```text
Complaint exists
```

→ به تنهایی Action نیست.

اما:

```text
Complaint ACTIVE
+
Purchase declining
+
Real Profit high
+
LTV high
```

→

**جلسه بررسی کیفیت با اولویت بالا**

---

# 01. Definition of Success

MVP موفق است اگر مدیر فروش بتواند روی یک مشتری کلیک کند و در کمتر از 30 ثانیه بفهمد:

> این مشتری چه وضعیتی دارد؟

> چه چیزی تغییر کرده؟

> آیا مشکل هنوز وجود دارد؟

> چرا برای من مهم است؟

> الان دقیقاً چه کاری باید انجام دهم؟

> سیستم بر چه اساسی این حرف را می‌زند؟

اگر این شش سؤال جواب داده شوند، محصول هسته اصلی مسئله هکاتون را حل کرده است.
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
