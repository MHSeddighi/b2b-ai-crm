from __future__ import annotations

import asyncio
import json
import os
import re
import sys
import time
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from openai import AsyncOpenAI, OpenAI

from backend.agents import contracts
from backend.agents.analysis import rank_discriminators
from backend.agents.context import SessionState, answer_preview
from backend.agents.contracts import CRM_TOOLS
from backend.agents.recommend import customer_signals, product_signals
from backend.agents.persian import fix_persian_zwnj
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
# Comparative/root-cause analysis (see PLANNER_SYSTEM) is a search for what
# discriminates two classes: it needs an entity query, a contrasting-class
# query, and comparisons across SEVERAL different tables/feature groups until
# an actual difference turns up — routinely 3-6 steps, not 1-2.
MAX_QUERIES = 7
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


CUST_INTEL_IDENTITY = """You are Cust Intel — the customer-intelligence unit of this product.

Cust Intel is ONE product made of two cooperating parts:
1. The Cust Intel SYSTEM (deterministic): the backend engine, DuckDB database,
   and the CRM/MCP tools. It alone computes every fact, signal, score,
   threshold, state, and action — always exactly, never guessed.
2. The LLM (you): the conversational part of the same product. You plan which
   tools to call, read the system's outputs, and explain/personalize them for
   the user. You NEVER compute or recalculate what the system computes.

So when you answer, you speak as Cust Intel: the numbers come from the system,
the words come from you, and together they are one answer from one product.
"""


PLANNER_SYSTEM = f"""{CUST_INTEL_IDENTITY}

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
- The system AUTOMATICALLY calls get_customer_action_plan for every customer
  the plan touches (the at-risk list and any per-customer tool). So do NOT
  add one get_customer_action_plan step per at-risk customer yourself — a
  single top_at_risk_customers step is enough, and the recommendations will
  be computed by the analysis engine for you.
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
- "reuse" is ONLY valid when the resultId is one of the exact ids already
  listed under "Relevant conversation context" below. Never invent, guess, or
  use a placeholder resultId (e.g. never write "previous_result_id" or similar)
  — if there is no earlier result that already contains the answer (including
  on the first turn of a conversation, when no results exist yet), use "query"
  instead.
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
- Each "query" step's SQL must be exactly ONE statement — never write two SELECT
  statements chained with ";" inside a single step's "query" field. If you need
  data from more than one table/query, add a SEPARATE step object to the
  "steps" array for each one — one step, one statement.
- Never use UNION/INTERSECT/EXCEPT to combine rows from different tables that
  represent different kinds of entities (e.g. dev_requests and offers, or
  orders and complaints) — DuckDB requires every branch to have the exact
  same number, order, and type of columns, and merging unrelated entities
  into one result table is not useful anyway. When a question needs signals
  from more than one such table (e.g. "sales and product-development
  opportunities"), plan one separate "query" step per table instead (this
  plan supports several query steps) — never SELECT * in a set operation.
  A set operation is only appropriate to merge rows that already share the
  exact same explicit column list from the same kind of query (e.g. the same
  SELECT list against two date ranges).
- If the question needs more than one query or may return a large result, that
  is fine — plan it. The assistant will let the user know it is processing in a
  few steps.

Root-cause / comparative analysis — think of it as binary classification:
- A question that asks WHY a metric is high/low, asks for factors/drivers/
  causes, asks for opportunities, or implies a judgment ("many", "few",
  "more", "worse", "better", "top", "best-selling", "bottom", "worst") is
  really asking you to find what DISCRIMINATES two classes:
    - the POSITIVE class: the entity/segment the question is actually about.
    - the CONTRASTING class: its natural opposite. Prefer an EXPLICIT
      opposite when the question has one — for "best-selling product", the
      contrast is the WORST-selling product (find it with its own query, e.g.
      ORDER BY the same metric ASC LIMIT 1), not just "everything else"; for
      "the product group with the most complaints", the contrast is the
      group with the FEWEST complaints. Fall back to "the rest of the
      population" only when there's no sharper natural opposite.
  Answering with only the positive class's own data can never explain
  anything — it can only describe it.
- You are hunting for the FACTOR OF DIFFERENCE, not the factor in common.
  Finding that some feature is SIMILAR between the two classes is not a
  finding — it gives the user nothing to act on. So:
    1. Compare the two classes on the ONE table most obviously related to the
       question first (e.g. quality_labs for a complaints/quality question,
       sales for a best-seller/worst-seller question).
    2. If that comparison comes back similar/inconclusive, do NOT stop there
       — plan MORE query steps checking OTHER tables/feature groups that
       could plausibly discriminate the two classes: pricing/discounts
       (offers, sales), customer segment/location (customers), payment
       behavior (collections), interaction patterns (crm_interactions),
       product development signals (dev_requests), market conditions
       (market_signals), quality (quality_labs) — pick whichever actually
       fit the schema and the question, and check SEVERAL of them.
    3. This usually means 3-6 query steps total for a real root-cause
       question, not 1-2 — use as many as needed (up to the limit) to
       actually FIND a discriminating factor, not just to describe one side.
- DON'T SPEND EVERY STEP ON THE SAME TABLE. Averaging two more numeric
  columns from a table that already came back near-identical will not
  suddenly reveal anything — that is a dead end, and repeating it is the most
  common way these plans fail. Numeric lab/measurement averages in particular
  are often nearly identical across groups. Always include at least one step
  on a DESCRIPTIVE/CATEGORICAL dimension, which is usually where real
  differences live: GROUP BY a category and compare the MIX/share between the
  two classes, e.g. products."دسته بندی براقیت" (luster class),
  products."گروه رنگ" (colour), products."زیرگروه کالا" (denier),
  complaints.Complaint_Title (which complaint TYPES dominate each class),
  complaints.Severity, customers.Customer_Segment, offers.Offer_Type. A
  categorical mix comparison ("70% of class A is luster 2 but only 23% of
  class B") is far more actionable than another pair of near-equal averages.
- EVERY comparison query MUST be an AGGREGATE query (COUNT, AVG, SUM, a
  percentage, GROUP BY) that returns a small summary — ONE row per class
  being compared, never a raw row-level join/list. This is critical: the
  analyst downstream only ever sees a handful of SAMPLE rows from a large
  raw result, so a raw join of thousands of rows is USELESS for comparison —
  it can't see enough of it to compute anything. An aggregate's single
  summary row is never truncated, so the exact number is always fully
  visible. NEVER plan
  "SELECT c.*, q.* FROM complaints c JOIN quality_labs q ... WHERE segment=X"
  for a comparison — plan
  "SELECT COUNT(*), AVG(q.Tensile_Strength_cN_dtex), ... FROM complaints c
  JOIN quality_labs q ... WHERE segment=X" (and the same shape for the
  contrasting class) instead.
  Worked example 1 — "why does group 3 have more complaints, what's
  different about it" (positive class = group 3, contrast = other groups):
  Step 1 (share of total): SELECT COUNT(*) FILTER (WHERE p."گروه کالا" =
  'Product_Family_03') * 100.0 / COUNT(*) AS pct_group3 FROM complaints c
  JOIN products p ON c.Product_ID = p.Product_ID
  Step 2 (quality comparison): SELECT p."گروه کالا" AS segment,
  AVG(q.Tensile_Strength_cN_dtex) AS avg_tensile, AVG(q.Elongation_Pct) AS
  avg_elongation FROM quality_labs q JOIN products p ON q.Product_ID =
  p.Product_ID GROUP BY p."گروه کالا"
  Step 3 (if step 2 was similar, try another table — pricing):
  SELECT p."گروه کالا" AS segment, AVG(s."قیمت فی فروش") AS avg_price,
  AVG(s."مقدار") AS avg_qty FROM sales s JOIN products p ON s.Product_ID =
  p.Product_ID GROUP BY p."گروه کالا"
  Worked example 2 — "what's our best-selling product" (implies: what makes
  it sell — positive class = the top seller, contrast = the bottom seller,
  found with its OWN query, not "the rest"):
  Step 1: SELECT Product_ID, SUM("مقدار") AS units FROM sales GROUP BY
  Product_ID ORDER BY units DESC LIMIT 1
  Step 2: SELECT Product_ID, SUM("مقدار") AS units FROM sales GROUP BY
  Product_ID ORDER BY units ASC LIMIT 1
  Step 3+: compare the two products' price, quality, offers, complaints,
  etc. — whichever tables plausibly explain the sales gap.
  Prefer computing the two classes in a SINGLE query when they share the
  same shape, e.g.
  SELECT 'گروه 3' AS segment, COUNT(*) AS n FROM complaints WHERE ...
  UNION ALL SELECT 'سایر گروه‌ها', COUNT(*) FROM complaints WHERE ...
  — both branches select the exact same columns, which is a normal,
  encouraged use of UNION ALL and different from the earlier rule against
  combining rows from unrelated entity tables. One result with both rows is
  easier to compare, chart, and reason about than two separate results.
- A plain factual lookup ("what is X", "show me Y", "list Z") does not need
  this — keep those to the minimum single query as before. This rule is only
  for questions that ask for an explanation, comparison, or judgment.

Data to support the closing recommendation:
- The assistant ALWAYS ends its answer with a short, concrete recommendation
  (which offer/product/discount to propose, what to investigate next, etc.).
  It can only do that honestly if you fetch the supporting data — otherwise
  it is forced to say "not enough data". So for an ENTITY-PROFILE question
  ("وضعیت مشتری X", "پروفایل X", "درباره محصول Y بگو"), don't stop at the one
  row describing the entity. Add 1-2 cheap AGGREGATE steps that make a
  recommendation possible, e.g. for a customer:
  * what they actually buy: SELECT Product_ID, SUM("مقدار") AS units,
    SUM("مبلغ کل") AS revenue FROM sales WHERE Customer_ID='<id>'
    GROUP BY 1 ORDER BY 2 DESC LIMIT 5
  * offers they've had and how they responded: SELECT Offer_Type, Result,
    COUNT(*) n, ROUND(AVG(Offer_Discount_Pct),3) avg_disc FROM offers
    WHERE Customer_ID='<id>' GROUP BY 1,2
  * what peers in the same segment buy / what discount they get, so the
    recommendation can be benchmarked rather than invented.
  For a product, the equivalent: who buys it, typical discount, complaint
  rate. Keep these aggregate and small.
"""


COMPOSER_SYSTEM = f"""{CUST_INTEL_IDENTITY}

You are now composing the final structured answer (blocks) for the user.

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
- The user is a NON-TECHNICAL sales manager: never mention "risk score",
  "algorithm", "signal", "score 92/100", "threshold", "backend", or any
  internal/technical term. Say what the facts mean in plain business words
  (e.g. "مدت‌هاست خرید نکرده", "شکایت باز دارد", "در پرداخت مشکل دارد").
- Persian orthography: ALWAYS write compound words with نیمفاصله (ZWNJ,
  U+200C), e.g. می‌شود، می‌کنند، حل‌نشده، جلسه‌ای، مشتری‌ها، یکی‌یکی — never
  join them without the half-space.
- Never invent or recalculate numbers.
- If the data is insufficient, say so clearly.
- Do not use headings like "Insight", "Finding", or "Analysis".
- Keep the answer concise and natural.
- When the results are numeric or a trend, always add a chart, metric, or table
  to visualize them — do not leave numbers as plain text alone.
- If an action plan is available for a customer (under "Deterministic customer
  intelligence" as an "action plan for <id>"), base the recommendation block on
  it — the recommended actions are computed by the analysis engine, and you
  may explain them in plain language but never change or invent them.
- If there is an assumption, reflect it naturally and briefly in the answer.
- Use the "markdown" type for prose (never "text"; the content field is
  "content"). Use "columns" (never "headers") in tables.
- If a result's n_rows is much larger than the handful of sample rows you were
  given, say plainly that the analysis reflects a representative sample of the
  full data, not an exhaustive count — describe patterns/trends qualitatively
  and never state a precise aggregate total (sum, exact count, exact
  percentage) you cannot verify from the sample rows you actually have.
- NEVER state a shallow, circular claim like "complaints are high because
  quality is low" or "quality is low because there are many complaints" — a
  reader could guess that without seeing any data, so it explains nothing.
  Every non-trivial claim must be grounded in a SPECIFIC number actually
  present in the results: a share/percentage of a total, a rate compared to
  a baseline/average/other group, or a concrete feature value that differs
  from the norm.
- When the results include both a class and its contrast (e.g. group 3 vs.
  other groups, best-seller vs. worst-seller), explicitly contrast them (e.g.
  "18% of complaints vs. an 11% baseline across other groups") — describing
  only one side is not analysis.
- Finding that a feature is SIMILAR between the two classes is not the
  finding — it's a checkpoint. If the results include several compared
  features, lead with whichever ones actually DIFFER (the real explanation),
  and only briefly mention the similar ones as ruled-out, in passing.
- Use a short bullet list for the concrete differentiating factors — e.g.
  "چیزهایی که گروه پرشکایت داره ولی گروه کم‌شکایت نداره" (what the
  high-complaint group has that the low-complaint one doesn't): each bullet
  one specific, numeric fact from the results.
- If the results you were given don't include the comparison needed to
  explain a "why", say plainly what IS known and that the cause isn't
  established by this data — never invent a causal claim you can't support.
- Do NOT write a 2-3 line answer for a comparative/root-cause question — that
  is too short to actually be useful. Give a fuller answer: a short direct
  opening, then the specific differentiating facts (as bullets), then what it
  means for the business. Keep the LANGUAGE simple and non-technical — the
  substance should be dense with real numbers, not the wording; don't pad
  with restatement or filler just to reach a length.
- ALWAYS finish with a "recommendation" block (2-3 lines), whatever the
  question was: a concrete suggested next action, not a restatement of the
  findings. E.g. for a customer profile, which product/offer type to put in
  front of them, roughly what discount level, or which payment/credit terms
  to propose; for a quality question, what to investigate or change.
  Ground it in the results (segment, credit limit, payment terms, discount
  levels actually present). If the data doesn't justify specifics, recommend
  the obvious next step instead — NEVER fabricate a discount percentage,
  price, or product name that isn't in the results.
"""


CHAT_SYSTEM = """
تو «کاست اینتل» (Cust Intel) هستی — واحد هوش مشتری همین محصول.

محصول ما یک واحد است از دو بخش که با هم کار می‌کنند:
1. سیستم کاست اینتل (قطعی): موتور پشتیبان، پایگاه‌داده DuckDB و ابزارهای CRM/MCP.
   تمام اعداد، سیگنال‌ها، امتیازها، آستانه‌ها و اقدام‌ها را فقط همین سیستم محاسبه
   می‌کند — همیشه دقیق، نه حدسی.
2. مدل زبانی (تو): بخش گفت‌وگوکنندهٔ همین محصول. تو برنامه‌ریزی می‌کنی کدام ابزار
   صدا زده شود، خروجی سیستم را می‌خوانی و برای کاربر توضیح می‌دهی. تو هرگز چیزی را
   که سیستم محاسبه کرده دوباره محاسبه یا تغییر نمی‌دهی.

پس وقتی پاسخ می‌دهی، به‌عنوان کاست اینتل حرف بزن: اعداد از سیستم، کلمات از تو، و
هر دو یک پاسخ از یک محصول هستند.
به فارسی و طبیعی صحبت کن.
کوتاه و مستقیم پاسخ بده.
از اصطلاحات فنی غیرضروری استفاده نکن.
همیشه کلمات مرکب را با نیم‌فاصله بنویس (می‌شود، می‌کنند، حل‌نشده، مشتری‌ها،
یکی‌یکی، جلسه‌ای) — هرگز بدون نیم‌فاصله.
اگر کاربر از «قطع شدن ارتباط»، «ارتباط با سرور»، «سرور پشتیبان»، «نتونست وصل بشه» یا
خطاهای مشابه در حین پاسخ‌گویی می‌پرسد، این مربوط به سرویس پشتیبان داخلی است، نه اینترنت
یا تلفن کاربر. عذرخواهی کن، توضیح بده که به‌طور موقت اختلالی پیش آمده و دوباره سؤالش را
بپرسد یا دوباره تلاش کند؛ از پرسیدن درباره اینترنت/سرویس‌دهنده خودداری کن.
"""


# Streaming narrative prompt: produces ONLY the natural-language answer as
# plain text (token-by-token). Structured blocks (charts/tables/metrics) are
# produced separately afterwards so the long text can stream in immediately.
NARRATIVE_SYSTEM = f"""{CUST_INTEL_IDENTITY}

You are now writing the natural-language narrative of the answer.

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
- Keep the answer natural, not padded — but see the length rule below for
  comparative/root-cause questions specifically.
- Mostly plain prose, but for a comparative/root-cause question use a
  markdown bullet list (up to 6-7 bullets) for the concrete differentiating
  facts found — e.g. "چیزهایی که گروه پرشکایت داره ولی گروه کم‌شکایت نداره"
  (what the high-X class has that the low-X class doesn't), each bullet one
  specific numeric fact from the results. NEVER use bullets/numbered lists or
  ASCII/Unicode bar charts (e.g. █ ██ ▌) to re-render row-level data,
  rankings, or distributions — that's what the chart/table/histogram blocks
  are for, so a bullet list of data rows/ranks would just duplicate a block.
- When the answer is large or took multiple steps (big data, several queries),
  briefly tell the user at a friendly level what is happening (e.g. "داده‌ها
  بزرگ است و پاسخ در چند مرحله آماده شد…") and then continue. Keep such notes
  short and natural.
- When discussing churn, at-risk customers, retention, or recommendations,
  speak to a NON-TECHNICAL sales manager in plain business language. NEVER
  mention "risk score", "algorithm", "signal", "score 92/100", "threshold",
  "backend", or any internal/technical term. Instead say what is actually
  happening in plain words, e.g. "این مشتری‌ها مدت‌هاست خرید نکرده‌اند",
  "شکایت‌های باز دارند", "در پرداخت‌ها مشکل داشته‌اند", "حجم خریدشان بالاست".
  Explain the WHY with the concrete facts from the results (last purchase
  date, complaint count, order volume, payment behaviour) — not with the
  machinery that computed them.
- Persian orthography: ALWAYS write compound words with نیمفاصله (ZWNJ,
  U+200C), e.g. می‌شود، می‌کنند، حل‌نشده، جلسه‌ای، مشتری‌ها، یکی‌یکی،
  به‌احتمال، پر‌ارزش، گرفته‌اند — never join them without the half-space.

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
- Every recommendation must be presented in plain business language for a
  NON-TECHNICAL reader: never mention the action id, "priority", "confidence",
  "signal", "score", "algorithm", or the tool names that produced it. Say the
  action as a human instruction (e.g. "با این مشتری تماس بگیرید و شکایتش را
  حل کنید", "به‌جای فروش اعتباری، پرداخت نقدی یا کوتاه‌تر پیشنهاد دهید").
- If a result's n_rows is much larger than the handful of sample rows you were
  given, say plainly that the analysis reflects a representative sample of the
  full data, not an exhaustive count — describe patterns/trends qualitatively
  and never state a precise aggregate total (sum, exact count, exact
  percentage) you cannot verify from the sample rows you actually have.
- NEVER state a shallow, circular claim like "complaints are high because
  quality is low" or "quality is low because there are many complaints" — a
  reader could guess that without seeing any data, so it explains nothing.
  Every non-trivial claim must be grounded in a SPECIFIC number actually
  present in the results: a share/percentage of a total, a rate compared to
  a baseline/comparison class, or a concrete feature value that differs.
- When the results compare a class against its contrast (e.g. group 3 vs.
  other groups, best-seller vs. worst-seller), explicitly contrast them (e.g.
  "18 درصد شکایات مربوط به این گروه است در حالی که میانگین سایر گروه‌ها 11
  درصد است") — describing only one side is not analysis.
- Finding a feature is SIMILAR between the two classes is not the finding —
  it's a checkpoint. Lead with whichever compared features actually DIFFER
  (that's the real explanation); mention similar ones only briefly, as
  ruled-out, in passing.
- If the results you were given don't include the comparison needed to
  explain a "why", say plainly what IS known and that the cause isn't
  established by this data — never invent a causal claim you can't support.
- Do NOT write a 2-3 line answer for a comparative/root-cause question — that
  is too short to be useful. Give a fuller answer: a short direct opening,
  then the specific differentiating facts (as bullets), then what it means
  for the business. Keep the LANGUAGE simple and non-technical — the
  substance should be dense with real numbers, not the wording; don't pad
  with restatement or filler just to reach a length. A plain factual
  question can still get a short answer — this length rule is specifically
  for "why"/comparison/opportunity questions.
- ALWAYS END WITH A SHORT RECOMMENDATION (2-3 lines), whatever the question
  was. After stating the facts, close with a concrete suggested next action
  for this business — not a summary restatement of what you just said. Make
  it specific and actionable, e.g. for a customer profile: which product or
  offer type to put in front of them, roughly what discount level, or which
  payment/credit term to propose; for a product/quality question: what to
  investigate or change; for a sales question: where the upside is.
  Ground it in the data you were given — reference the customer's segment,
  their credit/payment terms, what similar customers bought, the discount
  levels actually seen in the results, etc. If the results don't contain
  enough to justify specifics, keep the recommendation about the obvious
  next step (e.g. "برای پیشنهاد دقیق‌تر، سابقهٔ خرید و تخفیف‌های قبلی این
  مشتری را بررسی کنیم") rather than inventing a product, price, or discount
  number that isn't supported by the data. NEVER fabricate a specific
  discount percentage, price, or product name that does not appear in the
  results.
- When a "Measured recommendation signals" block is present, BUILD THE
  RECOMMENDATION ON IT — those numbers are computed from the full data and
  are the difference between a real proposal and generic advice. Work through
  whichever of these are present and actually matter for the question (not as
  a checklist — weave them into 3-6 natural sentences/bullets):
  * HEADROOM: name the untapped gap and the competitor holding it — that is
    the size of the opportunity ("we hold 41% of their spend; ~2,000 units
    sit with a local supplier").
  * CADENCE: say WHEN to approach and whether they are overdue. A customer
    far past their normal buying gap is a re-activation case, not a routine
    upsell — say so.
  * BUYS MOST: recommend a realistic QUANTITY anchored on their typical
    order size, and lead with products they already buy.
  * OPEN COMPLAINTS / DEVELOPMENT REQUESTS: if anything is unresolved, say
    it must be cleared or answered BEFORE pushing a new offer — an open
    complaint makes an upsell land badly.
  * HOW THEY PAY + COLLECTION: recommend cash/prepaid vs credit based on
    their real behaviour. Late settlement or any bounced cheque means
    propose cash/prepaid or shorter terms; a clean, fast-settling customer
    can be offered credit or longer terms.
  For a PRODUCT the same applies to its own signals:
  * DEMAND BY YEAR: say whether it is growing or declining, with the %.
    A sharp drop is a defend/re-launch case, not a routine upsell.
  * MARGIN: a thin margin means DON'T recommend deeper discounting — say so
    and push volume/value instead.
  * OFFER HISTORY: recommend the discount level that historically CLOSES,
    and give the accept rate — this is far better than "offer a discount".
  * CROSS-SELL WHITESPACE: name the number of same-family customers who
    never bought it — that is the concrete prospect list to work.
  * TOP BUYERS / concentration: flag dependence on one buyer as a risk.
  * COMPLAINTS / OPEN REQUESTS: unresolved items to clear first.
- If a "These exact values MUST appear" line is present, every one of those
  values HAS to show up in your recommendation. They are the difference
  between a proposal the manager can act on and generic advice — dropping
  the competitor's name, the volume, the margin or the closing discount
  makes the recommendation worthless. Do not omit any of them.
- Say the numbers plainly in the user's language; do not name the signal
  labels (HEADROOM/CADENCE/MARGIN/...) or mention that they were "computed".
"""


def _blocks_system(result_ids: str, has_crm: bool = False) -> str:
    crm_note = (
        """

CRM results are provided as JSON under "Deterministic customer intelligence"
below. Each is a table of backend-computed values (columns + rows). You MAY
build blocks from CRM data even when there are no resultIds: render them as
INLINE tables with explicit columns/rows (see table shape 4b) — the customer
names/ids, scores and values are exactly as given; never invent rows or
numbers.
"""
        if has_crm
        else ""
    )
    return f"""You are the data-visualization unit of Cust Intel, the
customer-intelligence product. You are the same product as the answering
assistant, but you specialize in turning results into structured blocks.

Given the results, pick the most useful blocks. When results are numeric or
tabular, ALWAYS add a visualization/card — never leave numbers as plain text.
Return [] only for purely conversational answers. Use ONLY the available
resultIds below; column names and id values must match the results EXACTLY
(never rename them).
{crm_note}
Available resultIds:
{result_ids}

Return ONLY a JSON array of blocks. Every block needs a unique "id". Shapes:

1. metric — one headline number:
   {{"type":"metric","id":"m1","resultId":"<id>","label":"فروش کل","valueKey":"<exact column>","rowIndex":0,"trend":"up"}}

2. chart — trend/category comparison: "line" for time trends, "bar" for categories, "scatter" for correlation:
   {{"type":"chart","id":"c1","resultId":"<id>","chartType":"line","xKey":"<exact column>","series":[{{"dataKey":"<exact column>","label":"فروش"}}],"title":"روند فروش ماهانه"}}

3. histogram — distribution of ONE numeric column (use when asked for histogram/distribution):
   {{"type":"histogram","id":"h1","resultId":"<id>","dataKey":"<exact numeric column>","bins":10,"title":"توزیع فروش"}}

4. table — ranked lists / multi-row detail:
   a) {{"type":"table","id":"t1","resultId":"<id>","title":"برترین مشتریان"}}
   b) {{"type":"table","id":"t1","columns":["<exact column names>"],"rows":[["<values>"],["<values>"]]}}  (use this for CRM data without a resultId)

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
- bar chart for a result comparing an entity against a baseline/other groups
  (a result with a segment/label column and 2+ rows to compare) — this is the
  most useful visual for "why"/comparison questions, prefer it over a table.
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
        default_headers=settings.extra_headers or None,
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


# Time budgets. Without these a single slow/hung tool call blocks the SSE
# stream indefinitely: the browser hits its own hard cap (240s in
# frontend/src/lib/chat-api.ts) and aborts, so the user loses the whole answer
# — including everything already gathered — and just sees "connection lost".
# Bounding each call, and the answer as a whole, turns that into a partial but
# delivered answer instead.
CRM_TOOL_TIMEOUT_S = 25.0
SQL_TIMEOUT_S = 60.0
# Keep the total comfortably under the frontend's hard abort so there is time
# left to compose and stream the narrative.
ANSWER_BUDGET_S = 150.0


class _Deadline:
    """Wall-clock budget for one answer."""

    def __init__(self, seconds: float = ANSWER_BUDGET_S) -> None:
        self.started = time.monotonic()
        self.seconds = seconds

    @property
    def remaining(self) -> float:
        return self.seconds - (time.monotonic() - self.started)

    @property
    def expired(self) -> bool:
        return self.remaining <= 0


async def _call_crm_tool(session: ClientSession, tool: str,
                         args: dict[str, Any],
                         trace: Trace | None = None,
                         timeout: float = CRM_TOOL_TIMEOUT_S) -> dict[str, Any]:
    """Invoke a deterministic CRM tool and parse its JSON result.

    Bounded by ``timeout``: a tool that never returns raises TimeoutError here
    instead of stalling the whole answer.
    """
    t0 = time.monotonic()
    try:
        response = await asyncio.wait_for(session.call_tool(tool, args), timeout)
    except (asyncio.TimeoutError, TimeoutError):
        if trace is not None:
            trace.tool(tool, args, {"error": "timeout"},
                       int((time.monotonic() - t0) * 1000), ok=False)
        raise
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


# How many at-risk customers get an automatically-chained action plan at most.
MAX_ACTION_PLANS = 10


async def _auto_chain_action_plans(
    crm_results: dict[str, Any],
    trace: Trace | None = None,
    deadline: "_Deadline | None" = None,
) -> list[str]:
    """Deterministically fetch action plans for customers the plan touched.

    The analysis system, not the LLM, decides which customers need a
    recommendation: every customer returned by ``top_at_risk_customers`` and
    every customer explicitly queried via the per-customer CRM tools gets a
    ``get_customer_action_plan`` call, stored under ``action_plan:<id>``. This
    guarantees the answer always recommends from the deterministic engine
    instead of relying on the model to remember to ask.

    Returns the list of customer ids chained (best-effort; never raises).
    """
    ids: list[str] = []
    for key, data in crm_results.items():
        if key.startswith("top_at_risk_customers:"):
            cols = data.get("columns", []) if isinstance(data, dict) else []
            if "Customer_ID" in cols:
                i = cols.index("Customer_ID")
                for row in (data.get("rows") or []):
                    if i < len(row) and row[i] and str(row[i]) not in ids:
                        ids.append(str(row[i]))
        elif key.startswith("get_customer_") and ":" in key:
            cid = key.split(":", 1)[1]
            if cid and cid not in ids:
                ids.append(cid)
    ids = ids[:MAX_ACTION_PLANS]
    if not ids:
        return []
    session = await _ensure_mcp()

    pending: list[str] = []
    for cid in ids:
        plan_key = f"action_plan:{cid}"
        direct_key = f"get_customer_action_plan:{cid}"
        # Already fetched by the plan's own step (key get_customer_action_plan:<id>)
        # or by a previous chaining pass (action_plan:<id>) — never call twice.
        if plan_key in crm_results:
            continue
        if direct_key in crm_results:
            crm_results[plan_key] = crm_results[direct_key]
            continue
        pending.append(cid)

    if not pending:
        return []

    # Fetched concurrently and under a shared budget: sequentially this was
    # N x tool-latency, so one slow customer used to push the whole answer past
    # the browser's abort. Whatever lands in time is used; the rest is dropped.
    async def fetch(cid: str) -> tuple[str, dict[str, Any] | None]:
        try:
            return cid, await _call_crm_tool(
                session, "get_customer_action_plan", {"customer_id": cid}, trace,
                timeout=CRM_TOOL_TIMEOUT_S,
            )
        except Exception:  # noqa: BLE001 - action plans are an enhancement
            return cid, None

    budget = deadline.remaining if deadline is not None else CRM_TOOL_TIMEOUT_S * 2
    tasks = [asyncio.create_task(fetch(cid)) for cid in pending]
    # asyncio.wait (not wait_for/gather) so that when the budget runs out we
    # still KEEP the plans that already came back — cancelling the stragglers
    # instead of discarding completed work along with them.
    done, still_running = await asyncio.wait(
        tasks, timeout=max(budget, 0.0), return_when=asyncio.ALL_COMPLETED
    )
    for task in still_running:
        task.cancel()

    chained: list[str] = []
    for task in done:
        try:
            cid, plan = task.result()
        except Exception:  # noqa: BLE001 - a failed plan is simply skipped
            continue
        if plan is not None:
            crm_results[f"action_plan:{cid}"] = plan
            chained.append(cid)
    return chained


async def _run_sql(sql: str) -> dict[str, Any]:
    """Execute ``sql`` against the shared MCP session.

    Resolves the session internally (never a stale reference) and, if the MCP
    server died mid-request (backend reload, subprocess crash), restarts it
    once and retries the query before giving up.
    """
    session = await _ensure_mcp()
    try:
        return await asyncio.wait_for(_call_query(session, sql), SQL_TIMEOUT_S)
    except (asyncio.TimeoutError, TimeoutError):
        # A query that never returns must surface as a normal error result, not
        # hang the stream until the browser gives up on the whole answer.
        await _restart_mcp()
        return {"error": f"query timed out after {SQL_TIMEOUT_S:.0f}s"}
    except Exception:
        await _restart_mcp()
        session = await _ensure_mcp()
        try:
            return await asyncio.wait_for(_call_query(session, sql), SQL_TIMEOUT_S)
        except (asyncio.TimeoutError, TimeoutError):
            return {"error": f"query timed out after {SQL_TIMEOUT_S:.0f}s"}


_SQL_FIX_SYSTEM = f"""You fix a failing DuckDB SQL query.

Database schema:
{CUSTOMER360_SCHEMA}

Return ONLY the corrected SQL (one read-only statement starting with SELECT or
WITH). No explanation, no markdown fences. Keep the same intent and result
columns. Common causes of the error:
- Column not found / "Binder Error" referencing a column that doesn't exist
  on that table (e.g. joining on a column only some tables have, like
  Sales_Line_ID which complaints does NOT have): the error's own "Candidate
  bindings" list is only what DuckDB found nearby — it is NOT the full
  picture. Use the schema above to find the column/table that actually has
  what you need (often the correct join key is Product_ID or Customer_ID
  instead, or requires going through a bridge table like complaint_links) —
  never guess a plausible-sounding column name.
- DuckDB reserved keywords used as identifiers/aliases (e.g. asof, range,
  qualify, sample, struct) — rename them to simple aliases like t1, base,
  max_date, total_amt.
- Casting a text/VARCHAR column (e.g. a Persian yes/no column like 'چک برگشتی'
  with values 'بله'/'خیر') to INT — filter with string literals instead.
- Wrong date function: use strftime(x, '%Y-%m') for formatting, CAST(col AS DATE)
  for date math; single quotes for strings, double quotes for identifiers.
- Multiple statements chained with ";" ("Only single read-only SELECT / WITH
  ... SELECT queries are allowed"): return ONLY the first statement, rewritten
  as a complete, valid, standalone query — drop everything after the first ";".
- UNION/INTERSECT/EXCEPT with mismatched columns ("Set operations can only
  apply to expressions with the same number of result columns"): the branches
  are almost always different, unrelated tables that should never have been
  combined this way. Do NOT invent placeholder/NULL columns to force them to
  align. Instead, drop the set operation entirely and return ONLY the first
  branch's SELECT (rewritten as a complete, valid, standalone statement,
  never leaving "..." or any other placeholder in the column list)."""


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


# A query that matched zero rows is only worth retrying with a loosened
# filter when it actually contains a quoted-literal equality/IN comparison —
# the likely culprit when a categorical/text column's real value format
# doesn't match what the user (or the planner) guessed (e.g. "3" vs
# "Product_Family_03"). Numeric/date-only filters are left alone: a genuine
# "no data" answer there should stay a "no data" answer.
_QUOTED_FILTER_RE = re.compile(r"=\s*'[^']*'|\bIN\s*\(\s*'", re.IGNORECASE)


def _has_quoted_filter(sql: str) -> bool:
    return bool(_QUOTED_FILTER_RE.search(sql))


_SQL_LOOSEN_SYSTEM = """A DuckDB query ran successfully but matched zero rows.
This usually means an equality/IN filter used the wrong literal value or
format for a text/categorical column (e.g. matching a bare number like '3'
against a column that actually stores padded/prefixed labels like
'Product_Family_03').

Return ONLY the corrected SQL (one read-only statement starting with SELECT or
WITH). No explanation, no markdown fences. Keep the same intent and result
columns.

Guidance:
- Replace exact equality on a text/categorical column with a case-insensitive
  partial match, e.g. WHERE col = '3' -> WHERE col ILIKE '%3%'.
- Only loosen filters that plausibly caused the empty result (quoted
  string literals compared with = or IN); never change numeric range
  filters, date filters, or joins.
- If you cannot identify a filter to loosen, return the original query
  unchanged."""


def _sql_loosen_prompt(question: str, sql: str) -> str:
    return f"""A DuckDB query ran successfully but matched zero rows.

User question:
{question}

Query that returned zero rows:
{sql}

Rewrite it with a loosened filter so it can find the intended rows. Return
ONLY the corrected SQL."""


async def _loosen_sql(question: str, sql: str) -> str | None:
    """Ask the LLM to loosen a likely-mismatched filter once. None if it can't."""
    try:
        raw = await _llm_call_async(_SQL_LOOSEN_SYSTEM, _sql_loosen_prompt(question, sql), temperature=0.0)
    except Exception:  # noqa: BLE001 - best effort
        return None
    loosened = (raw or "").strip().strip("`")
    lowered = loosened.lower()
    if not (lowered.startswith("select") or lowered.startswith("with")):
        return None
    return loosened


async def _exec_query(question: str, sql: str,
                      trace: Trace | None = None) -> dict[str, Any]:
    """Run a query; if it returns an SQL error, ask the LLM to fix it once and
    retry. If it succeeds but matches zero rows and has a quoted-literal
    filter, ask the LLM to loosen that filter once and retry. Returns the
    original result if no recovery helps, so genuine failures/empty answers
    stay explicit instead of silently changing the question."""
    t0 = time.monotonic()
    data = await _run_sql(sql)
    current_sql = sql

    if data.get("error"):
        fixed = await _fix_sql(question, sql, data["error"])
        if fixed and fixed.strip().lower() != sql.strip().lower():
            data2 = await _run_sql(fixed)
            if not data2.get("error"):
                data = data2
                current_sql = fixed
        if data.get("error"):
            if trace is not None:
                trace.tool("query", {"sql": sql}, data,
                           int((time.monotonic() - t0) * 1000), ok=False,
                           error=data.get("error", ""))
            return data

    if not data.get("n_rows") and _has_quoted_filter(current_sql):
        loosened = await _loosen_sql(question, current_sql)
        if loosened and loosened.strip().lower() != current_sql.strip().lower():
            data2 = await _run_sql(loosened)
            if not data2.get("error") and data2.get("n_rows"):
                if trace is not None:
                    trace.tool("query", {"sql": sql, "loosened_sql": loosened}, data2,
                               int((time.monotonic() - t0) * 1000), ok=True)
                return data2

    if trace is not None:
        trace.tool("query", {"sql": sql}, data,
                   int((time.monotonic() - t0) * 1000),
                   ok=not data.get("error"), error=data.get("error", ""))
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


def _invalid_reuse_id(plan: dict[str, Any], ctx: SessionState) -> str | None:
    """Return the first "reuse" resultId in ``plan`` that doesn't actually
    exist in this session (e.g. a hallucinated placeholder id), or None if
    every "reuse" step is valid."""
    for step in plan["steps"]:
        if step["kind"] == "reuse":
            result_id = step.get("resultId")
            if not result_id or ctx.get_result(result_id) is None:
                return result_id or "(missing)"
    return None


def _replan_prompt(question: str, ctx: SessionState, invalid_result_id: str) -> str:
    context = ctx.render_context(
        question,
        active_ids=ctx.active_result_ids(),
    )

    return f"""
Your previous plan used "reuse" with resultId "{invalid_result_id}", but no
such result exists in this conversation (it may not exist yet — e.g. this is
the first turn — or the id was invented). Produce a corrected plan: if data is
needed, use "query" to run SQL directly instead of "reuse". Never invent or
guess a resultId.

User question:
{question}

Relevant conversation context (includes earlier results referenced by their
resultId):
{context}

Return ONLY valid JSON.
"""


async def _replan_without_reuse(
    question: str,
    ctx: SessionState,
    invalid_result_id: str,
) -> dict[str, Any]:
    raw = await _llm_call_async(
        PLANNER_SYSTEM,
        _replan_prompt(question, ctx, invalid_result_id),
        temperature=0.0,
    )
    return _plan_from_raw(raw)


# The PLANNER_SYSTEM prompt asks for a comparison/baseline query on "why" /
# comparison / opportunity questions, but this model doesn't reliably follow
# that on its own (observed: it kept planning a single entity-only query even
# with the rule spelled out). This is a deterministic backstop: detect the
# question is asking for an explanation/comparison from the planner's own
# intent + step purposes, and if it only planned one query, force one more
# LLM call whose only job is to add a baseline/comparison step.
_COMPARATIVE_INTENT_RE = re.compile(
    r"\b(why|reason|relationship|compare|comparison|factor|driver|cause|"
    r"opportunit|impact|correlat|root[ -]?cause|versus|vs\.?|"
    r"higher|lower|worse|better|more\s+than|less\s+than|trend)\b"
    r"|چرا|دلیل|علت|رابطه|ارتباط|مقایسه|فرصت|عامل",
    re.IGNORECASE,
)


# A question naming a concrete entity id (C_123456 / P_003511 / CUST-019) or
# asking about stored records is a data question — an empty plan there means
# the planner bailed out, not that no data was needed. Seen in practice: the
# long planner prompt occasionally yields zero steps for "از وضعیت مشتری
# C_683666 بگو", which then falls through to a generic chat reply.
_ENTITY_ID_RE = re.compile(r"\b[A-Za-z]{1,6}[_-]\d{3,}\b")


def _plan_missing_data(question: str, plan: dict[str, Any]) -> bool:
    """True when an empty plan almost certainly should have queried."""
    if plan["steps"]:
        return False
    return bool(_ENTITY_ID_RE.search(question))


def _force_query_prompt(question: str, ctx: SessionState) -> str:
    context = ctx.render_context(question, active_ids=ctx.active_result_ids())
    return f"""Your previous plan returned no steps, but this question names a
specific record in the database and cannot be answered without looking it up.

User question:
{question}

Relevant conversation context:
{context}

Produce a plan with at least one "query" step that fetches the entity, plus
1-2 small AGGREGATE steps giving the context needed to end with a concrete
recommendation (what they buy, offers/discounts they've had, or how they
compare to peers in the same segment).

Return ONLY valid JSON in the plan format."""


async def _replan_for_data(
    question: str,
    ctx: SessionState,
    plan: dict[str, Any],
) -> dict[str, Any]:
    try:
        raw = await _llm_call_async(
            PLANNER_SYSTEM, _force_query_prompt(question, ctx), temperature=0.0
        )
        new_plan = _plan_from_raw(raw)
    except Exception:  # noqa: BLE001 - keep the original plan on failure
        return plan
    return new_plan if new_plan["steps"] else plan


def _needs_comparison(plan: dict[str, Any]) -> bool:
    query_steps = [s for s in plan["steps"] if s["kind"] == "query"]
    if len(query_steps) >= 3:
        return False  # already has room to compare across more than one table
    text = plan.get("intent", "") + " " + " ".join(s.get("purpose", "") for s in query_steps)
    return bool(_COMPARATIVE_INTENT_RE.search(text))


def _comparison_prompt(question: str, ctx: SessionState, plan: dict[str, Any]) -> str:
    context = ctx.render_context(question, active_ids=ctx.active_result_ids())
    existing_sql = "\n".join(
        f"- {s['sql']}" for s in plan["steps"] if s["kind"] == "query"
    )

    return f"""Your plan for this question doesn't yet check enough to find
what actually DISCRIMINATES the two classes involved — it either has no
contrasting class at all, or only checked ONE table/feature group. Describing
one side, or finding one similar feature and stopping, explains nothing.

User question:
{question}

Relevant conversation context:
{context}

Your current query step(s):
{existing_sql}

Rewrite the plan, keeping any existing step(s) that are still useful, and
adding 1-3 MORE "query" steps so the plan:
1. Has an explicit CONTRASTING class if it's missing — the natural opposite
   of the entity in the question (e.g. worst-seller for a best-seller
   question, the lowest-X group for a highest-X question), not just "the
   rest" unless there's no sharper opposite.
2. Checks the two classes across a DIFFERENT table/feature group than
   whatever was already queried (pricing/offers, customer segment, payment
   behavior/collections, interaction patterns/crm_interactions, product
   development/dev_requests, market conditions/market_signals, quality —
   pick whichever are relevant and not yet checked) — the goal is to find a
   feature that actually DIFFERS between the two classes, not to repeat the
   same comparison again.

Every new step MUST be an AGGREGATE query (COUNT, AVG, SUM, a percentage,
GROUP BY) returning a small summary — ONE row per class being compared —
NEVER a raw row-level join/copy of an existing step's SELECT list with a
different filter. A raw join of thousands of rows is useless here: the
downstream analyst only ever sees a handful of sample rows from a large
result, so the real comparison number would be invisible. If an existing
step is also a raw row-level query, rewrite it as an aggregate too.

Return ONLY valid JSON in the same plan format, with all steps in "steps"."""


async def _add_comparison_step(
    question: str,
    ctx: SessionState,
    plan: dict[str, Any],
) -> dict[str, Any]:
    try:
        raw = await _llm_call_async(
            PLANNER_SYSTEM,
            _comparison_prompt(question, ctx, plan),
            temperature=0.0,
        )
        new_plan = _plan_from_raw(raw)
    except Exception:  # noqa: BLE001 - fall through with the original plan
        return plan

    old_queries = len([s for s in plan["steps"] if s["kind"] == "query"])
    new_queries = len([s for s in new_plan["steps"] if s["kind"] == "query"])
    # Only accept the rewrite if it actually grew — otherwise keep the
    # original rather than risk losing a working step to a worse rewrite.
    return new_plan if new_queries > old_queries else plan


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

    invalid_id = _invalid_reuse_id(plan, ctx)
    if invalid_id:
        try:
            plan = await _replan_without_reuse(question, ctx, invalid_id)
        except Exception:  # noqa: BLE001 - fall through with the original plan
            pass

    if _plan_missing_data(question, plan):
        plan = await _replan_for_data(question, ctx, plan)

    if _needs_comparison(plan):
        plan = await _add_comparison_step(question, ctx, plan)

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
    invalid_id = _invalid_reuse_id(plan, ctx)
    if invalid_id:
        try:
            plan = await _replan_without_reuse(question, ctx, invalid_id)
        except Exception:  # noqa: BLE001 - fall through with the original plan
            pass

    if _plan_missing_data(question, plan):
        plan = await _replan_for_data(question, ctx, plan)

    if _needs_comparison(plan):
        plan = await _add_comparison_step(question, ctx, plan)

    if trace is not None:
        trace.plan(plan["intent"], plan["steps"], plan["assumption"])
    yield ("plan", plan)


def _render_action_plan(data: dict[str, Any]) -> str:
    """Compact human-readable rendering of one get_customer_action_plan result.

    Keeps the deterministic recommendation (state summary + top actions) small
    enough to inline into a prompt even for several customers at once.
    """
    parts: list[str] = []
    cid = data.get("customer_id") or "?"
    state = data.get("state") or {}
    if isinstance(state, dict):
        dims = []
        for dim, val in state.items():
            if isinstance(val, dict) and val.get("status"):
                dims.append(f"{dim}={val.get('status')}")
        if dims:
            parts.append(f"state: {', '.join(dims)}")
    actions = data.get("next_best_actions") or []
    for a in actions[:3]:
        if not isinstance(a, dict):
            continue
        name = a.get("name") or a.get("action_id") or "?"
        reason = a.get("reason") or ""
        step = a.get("suggested_next_step") or ""
        priority = a.get("priority")
        line = f"- {name}"
        if priority is not None:
            line += f" (priority {priority})"
        if reason:
            line += f": {reason}"
        if step:
            line += f" -> {step}"
        parts.append(line)
    if not parts:
        parts.append("(no recommended actions)")
    return f"action plan for {cid}:\n" + "\n".join(parts)


def _fix_blocks_text(blocks: list[dict]) -> list[dict]:
    """Restore Persian نیمفاصله (ZWNJ) in user-facing block text.

    LLM output frequently drops ZWNJ (حلنشده instead of حلنشده, جلسهی instead
    of جلسهای). Fix markdown/recommendation content deterministically before
    it reaches the UI.
    """
    out: list[dict] = []
    for b in blocks:
        b = dict(b)
        btype = b.get("type")
        if btype in ("markdown", "recommendation"):
            for field in ("content", "text", "title", "reason"):
                if isinstance(b.get(field), str):
                    b[field] = fix_persian_zwnj(b[field])
        elif btype == "table":
            if isinstance(b.get("title"), str):
                b["title"] = fix_persian_zwnj(b["title"])
        out.append(b)
    return out


def _render_crm(crm_results: dict[str, Any], max_chars: int = 2500) -> str:
    """Render deterministic CRM tool results as a compact block.

    ``action_plan:*`` entries (auto-fetched per customer) are rendered with
    ``_render_action_plan`` so several plans fit in one prompt; everything else
    is dumped as JSON truncated to ``max_chars``.
    """
    if not crm_results:
        return ""
    parts: list[str] = []
    for key, data in crm_results.items():
        if key.startswith("action_plan:"):
            parts.append(_render_action_plan(data))
            continue
        js = json.dumps(data, ensure_ascii=False, default=str)
        parts.append(f"CRM result [{key}]:\n{js[:max_chars]}")
    return "\n\n".join(parts)


# Customer ids are "C_" + digits and product ids start "P_" (see the schema
# rules), so the prefix alone tells us which signal set to compute.
_CUSTOMER_ID_RE = re.compile(r"\bC[_-]\d{3,}\b", re.IGNORECASE)
_PRODUCT_ID_RE = re.compile(r"\bP_[A-Za-z0-9_]{3,30}\b")


def _find_entity_id(
    pattern: re.Pattern[str],
    question: str,
    results: dict[str, SqlResult],
    id_columns: tuple[str, ...],
) -> str | None:
    """Locate an entity id in the question, else in the fetched results.

    The id is often not typed by the user at all ("our best-selling product"),
    so falling back to the top row of a matching id column is what makes the
    signals fire on those questions too.
    """
    match = pattern.search(question)
    if match:
        return match.group(0)
    for sr in results.values():
        for col_i, col in enumerate(sr.columns):
            if col.lower().replace("_", "") not in id_columns:
                continue
            for row in sr.rows[:1]:
                if col_i < len(row) and row[col_i]:
                    found = pattern.search(str(row[col_i]))
                    if found:
                        return found.group(0)
    return None


async def _recommendation_signals(question: str, results: dict[str, SqlResult]) -> str:
    """Measured signals backing the closing recommendation.

    Computed here rather than left to the model: asked to recommend without
    these, it produces advice that could have been written without seeing the
    data ("offer an attractive discount"). Customer- and product-focused
    questions get their own signal sets, and a question naming both (e.g.
    "should we sell P_x to C_y") gets both. Never raises — a failure here just
    means the answer closes with a softer recommendation.
    """
    blocks: list[str] = []
    try:
        cid = _find_entity_id(_CUSTOMER_ID_RE, question, results, ("customerid",))
        if cid:
            blocks.append(await customer_signals(cid, _run_sql))
        pid = _find_entity_id(_PRODUCT_ID_RE, question, results, ("productid",))
        if pid:
            blocks.append(await product_signals(pid, _run_sql))
    except Exception:  # noqa: BLE001 - signals are an enhancement, never fatal
        return ""
    return "\n".join(b for b in blocks if b)


def _discriminator_summary(results: dict[str, SqlResult]) -> str:
    """Pre-computed ranking of which features separate the compared classes.

    Handed raw comparison rows, the model tends to fixate on the first metric
    it sees and call the classes "similar". Computing the gaps here — and
    naming the ruled-out features explicitly — removes that guesswork.
    """
    parts = [
        text
        for sr in results.values()
        if (text := rank_discriminators(sr.columns, sr.rows))
    ]
    if not parts:
        return ""
    return (
        "\nMeasured comparison (computed exactly from the FULL data, not a "
        "sample — trust these gaps over your own reading of the rows):\n"
        + "\n".join(parts)
    )


def _compose_prompt(
    question: str,
    ctx: SessionState,
    results: dict[str, SqlResult],
    assumption: str,
    crm_results: dict[str, Any] | None = None,
    signals: str = "",
) -> str:
    context = ctx.render_context(
        question,
        active_ids=[],
    )

    samples = ctx.result_samples(
        list(results.keys())
    )

    crm_block = _render_crm(crm_results or {}, max_chars=9000)

    return f"""
User question:
{question}

Conversation context:
{context}

Assumption:
{assumption or "none"}

Results:
{samples}
{_discriminator_summary(results)}
{signals}

Deterministic customer intelligence (computed by the Cust Intel system — do
NOT recalculate or invent; use these values verbatim for any recommendation):
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
    signals = await _recommendation_signals(question, results)
    raw = await _llm_call_async(
        COMPOSER_SYSTEM,
        _compose_prompt(
            question,
            ctx,
            results,
            assumption,
            crm_results,
            signals,
        ),
        temperature=0.2,
        trace=trace,
        call="composer",
    )

    parsed = contracts.parse_blocks_json(raw)

    if isinstance(parsed, list):
        return _fix_blocks_text(parsed)

    return [
        {
            "id": "b1",
            "type": "markdown",
            "content": fix_persian_zwnj(str(raw)),
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
            _fix_blocks_text(
                [
                    {
                        "id": "b1",
                        "type": "markdown",
                        "content": raw,
                    }
                ]
            )
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

    # Deterministic chaining: any customer the plan touched (at-risk list or
    # per-customer tools) automatically gets its action plan fetched, so the
    # recommendation always comes from the analysis engine.
    if trace is not None:
        trace.stage("actions", "در حال محاسبه اقدام‌های پیشنهادی")
    try:
        await _auto_chain_action_plans(crm_results, trace)
    except Exception:  # noqa: BLE001 - chaining is an enhancement, never fatal
        pass

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

    # Retry once if the connection drops before any content has arrived (the
    # gateway can occasionally reset a freshly opened stream). Once content
    # has started arriving we never retry, to avoid duplicating output.
    last_exc: Exception | None = None
    for attempt in range(2):
        client = AsyncOpenAI(
            api_key=settings.api_key,
            base_url=settings.resolved_base_url,
            default_headers=settings.extra_headers or None,
        )
        yielded_any = False
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
                    yielded_any = True
                    yield delta.content
            return
        except Exception as exc:  # noqa: BLE001 - retried once below
            last_exc = exc
            if yielded_any:
                raise
        finally:
            await client.close()
    if last_exc:
        raise last_exc


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
    signals: str = "",
) -> str:
    context = ctx.render_context(question, active_ids=[])
    samples = ctx.result_samples(list(results.keys()))
    crm_block = _render_crm(crm_results or {}, max_chars=9000)
    return f"""
User question:
{question}

Conversation context:
{context}

Assumption:
{assumption or "none"}

Results:
{samples}
{_discriminator_summary(results)}
{signals}

Deterministic customer intelligence (computed by the Cust Intel system; do
NOT recalculate or invent — use these values verbatim for any recommendation):
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
    crm_block = _render_crm(crm_results or {}, max_chars=9000)
    return f"""
User question:
{question}

Conversation context:
{context}

Assumption:
{assumption or "none"}

Results:
{samples}

Deterministic customer intelligence (backend-computed, from the Cust Intel
system — build tables/cards from these values; never invent rows or numbers):
{crm_block or "(none)"}

Return ONLY a JSON array of blocks (non-markdown). Use only the available
resultIds; for CRM data with no resultId use inline tables (columns+rows).
Return an empty array if no block genuinely improves the answer.
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
        signals = await _recommendation_signals(question, results or {})
        user = _narrative_prompt(question, ctx, results or {}, assumption, crm_results, signals)
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
    """Produce optional structured blocks (charts/tables/metrics) at the end.

    Runs for SQL results AND/OR CRM tool results: CRM-only answers (e.g. the
    at-risk customer list) must still render as tables even though there are
    no SQL resultIds to reference.
    """
    crm_results = crm_results or {}
    if not results and not crm_results:
        return []
    raw = await _llm_call_async(
        _blocks_system(", ".join(results.keys()), has_crm=bool(crm_results)),
        _blocks_prompt(question, ctx, results, assumption, crm_results),
        temperature=0.0,
        trace=trace,
        call="blocks",
    )
    parsed = contracts.parse_blocks_json(raw)
    if isinstance(parsed, list):
        return _fix_blocks_text([b for b in parsed if b.get("type") != "markdown"])
    return []


async def _database_answer_stream(
    question: str,
    ctx: SessionState,
    trace: Trace | None = None,
) -> Any:
    """Yield SSE-style event dicts for the full database-backed answer."""
    deadline = _Deadline()
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

        # Out of budget: stop gathering and answer with what we already have.
        # A partial answer beats the browser aborting and showing nothing.
        if deadline.expired and (results or crm_results):
            yield {
                "type": "thinking",
                "text": "بررسی طولانی شد؛ با همین داده‌های به‌دست‌آمده پاسخ را آماده می‌کنم…",
            }
            break

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

    # Deterministic chaining: any customer the plan touched automatically gets
    # its action plan fetched, so recommendations come from the engine.
    if trace is not None:
        trace.stage("actions", "در حال محاسبه اقدام‌های پیشنهادی")
        for ev in trace.drain():
            yield {"type": ev["t"], **{k: v for k, v in ev.items() if k not in ("t", "ts")}}
    try:
        await _auto_chain_action_plans(crm_results, trace, deadline)
    except Exception:  # noqa: BLE001 - chaining is an enhancement, never fatal
        pass
    if trace is not None:
        for ev in trace.drain():
            yield {"type": ev["t"], **{k: v for k, v in ev.items() if k not in ("t", "ts")}}

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

    # Accumulated so the turn can be recorded into session memory exactly once
    # below, regardless of which path this generator exits through (success,
    # a graceful "error" event, or a hard exception) — every previous early
    # exit silently skipped this, which is why follow-up questions like
    # "خلاصه بده" lost all context after any failed turn.
    narrative = ""
    blocks: list[Any] = []
    error_message: str | None = None

    try:
        async for event in _database_answer_stream(question, ctx, trace):
            et = event.get("type")
            if et == "text":
                narrative += event.get("text", "")
            elif et == "blocks":
                blocks = event.get("blocks") or []
            elif et == "error":
                error_message = event.get("message")
            yield event
        yield {"type": "done"}
    except Exception as exc:  # noqa: BLE001
        # Hard failure: drop the cached MCP session so the next request
        # restarts it cleanly instead of reusing a broken connection.
        await close_mcp()
        error_message = f"در پاسخ‌گویی مشکلی پیش آمد: {exc}"
        yield {"type": "error", "message": error_message}
        yield {"type": "done"}
    finally:
        preview = error_message or answer_preview(
            [{"id": "b0", "type": "markdown", "content": narrative}] + blocks
        )
        ctx.record_turn(question, preview)


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
        result = await _database_answer(
            question,
            ctx,
            trace,
        )

    except Exception as exc:
        # If the MCP server died, drop the cached session so the next request
        # restarts it cleanly instead of reusing a broken connection.
        await close_mcp()
        result = _error(
            f"در پاسخ‌گویی مشکلی پیش آمد: {exc}"
        )

    # Record the turn regardless of success/failure, so a follow-up question
    # always has context of what was just asked (and whether it failed).
    ctx.record_turn(question, answer_preview(result.get("blocks", [])))
    return result