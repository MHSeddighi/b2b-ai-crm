# Signals & Decision Engine — Reference

> **Persistent technical context.**
> Before modifying any signal, threshold, state dimension, action, ranking rule, or the
> deterministic engine pipeline, read this file first.
>
> Code lives under `backend/crm/`. The engine is **deterministic** — everything is computed
> in Python/SQL from real data. The LLM only *consumes* and *explains* engine output; it
> never computes a signal, score, threshold, or action.

---

## 1. What This Is

The engine is the **deterministic Customer Intelligence layer** of the B2B AI CRM.
For every customer it turns raw transactional data (sales, collections, complaints,
offers, wallet-share estimates, dev requests) into:

1. **Signals** — measurable facts (`profit`, `purchase_trend`, `churn_risk`, …).
2. **State** — six interpretable dimensions (`value`, `churn_risk`, `growth_opportunity`,
   `relationship_health`, `profitability`, `payment_risk`).
3. **Reasons** — citable, structured *why* statements (evidence + source signals).
4. **Actions** — a ranked, eligibility-checked **Next Best Action** list.

The pipeline is one direction, computed in one pass:

```text
Raw DuckDB tables
      │
      ▼
Signal Engine (9 base + 2 derived signals)
      │
      ├──► State dimensions        (customer_state.py)
      ├──► Reasons / evidence      (reason_engine.py)
      ├──► Data quality            (service.py)
      │
      ▼
Decision Engine — Next Best Action
      │
      ├──► Eligibility  (declarative conditions, forbidden overrides)
      ├──► Ranking      (priority = business_impact × urgency × confidence × data_quality)
      │
      ▼
Ranked actions (top 3 by default) ──► LLM tools / MCP / REST API / Dashboard
```

### Core files

| File | Role |
| --- | --- |
| `backend/crm/schemas.py` | Canonical pydantic contracts (Signal, State, Reason, Action, Intelligence) |
| `backend/crm/config.py` | **All** business thresholds, centrally configurable |
| `backend/crm/data.py` | Read-only DuckDB access + shared helpers (windows, pct change, fingerprint) |
| `backend/crm/engine.py` | `SignalEngine` — one pass, one connection, base → derived |
| `backend/crm/signals/` | One module per signal + registry (`BASE_SIGNALS`, `DERIVED_SIGNALS`) |
| `backend/crm/state/` | `build_state` (6 dimensions) + `build_reasons` (reason/evidence layer) |
| `backend/crm/actions/` | Declarative action catalog, eligibility evaluator, ranking, NBA engine |
| `backend/crm/service.py` | Orchestration + data-quality assessment + 5 tool accessors |
| `backend/crm/at_risk.py` | Portfolio-level churn ranking (real engine signals, cached) |
| `backend/crm/cache.py` | JSON file cache invalidated by a data fingerprint |
| `backend/crm/labels.py` | Persian labels + deterministic reason translator (API boundary) |
| `backend/crm/tools.py` / `backend/mcp/duckdb_server.py` | LLM-facing tool surface (JSON) |

---

## 2. Design Principles

1. **Deterministic first, ML never by default.** Every score is computed from real data by
   explicit rules. No black box. (Advanced models may be added only if the data proves them
   necessary — see `docs/customer-intelligence-analysis.md`.)
2. **Explainable.** Every signal carries `evidence`, `reasons`, `confidence`, `sample_size`.
   Every action carries a deterministic reason + evidence. The UI and chatbot can explain
   *why* without calling the LLM.
3. **Config over code.** Nothing business-critical is hard-coded in signal/action logic; the
   business team tunes `backend/crm/config.py` and `backend/crm/actions/definitions.py`.
4. **Honest degradation.** A missing table, missing cost data, or tiny samples never produces
   a confident guess: signals return `status="unknown"` / `confidence=0` and reasons state
   exactly what is missing. Profit is never faked from revenue; share-of-wallet is never
   reconstructed from our own sales (circular).
5. **No double counting.** Correlated signals (e.g. purchase trend + purchase cycle) are
   grouped before scoring so one underlying decline is counted once.
6. **The LLM consumes, never computes.** The chatbot may only explain/personalize the
   engine's values. Tools (`get_customer_signals`, `get_next_best_actions`, …) enforce this.

---

## 3. Data Layer & Shared Helpers (`data.py`)

- One **read-only** DuckDB connection per customer pass (`SET enable_external_access=false`).
- A single **reference date** (`reference_date` = dataset's latest sale date) is passed to
  every signal so all signals agree on what "now" means.
- Helpers: `window_bounds(ref, days)` (inclusive trailing window), `pct_change(current,
  previous)` (None when baseline is 0 — never divide by zero), `safefloat`, `as_date`,
  `customer_exists`.
- `global_fingerprint(con)` — cheap hash of row counts + newest dates of the main tables;
  used to invalidate portfolio caches (`at_risk`, dashboards) automatically.

---

## 4. The Signals — Full Catalog

Signals are registered in `backend/crm/signals/__init__.py`:

- **BASE_SIGNALS** (computed from the DB, stable order): `profit`, `purchase_trend`,
  `payment_behavior`, `share_of_wallet`, `purchase_cycle`, `margin_trend`, `offer_affinity`,
  `complaint_impact`, `dev_request`.
- **DERIVED_SIGNALS** (consume base results): `growth_potential`, `churn_risk`.

Every signal is a `CustomerSignal`:

```python
signal_id, customer_id,
score (0..100), value (raw), status (positive|neutral|warning|critical|unknown),
direction (improving|stable|declining|neutral|unknown),
confidence (0..1), sample_size, evidence{...}, reasons[...]
```

### ⭐ Importance ranking of the signals

Ordered by **decision impact**: how many actions/dimensions depend on a signal, how much
weight it carries inside derived signals, how severe the consequence of missing it is, and
how uniquely it covers a dimension. **(1 = most important).**

| # | Signal | Why it ranks here |
| --- | --- | --- |
| 1 | `churn_risk` (derived) | The synthesis of everything else. Gates `RETENTION_CALL`, `ACCOUNT_REVIEW`, `LOYALTY_OFFER`; drives the portfolio at-risk ranking and dashboard risk levels. |
| 2 | `profit` | The financial ground truth. Feeds `profitability`, `value`, `growth_potential`, and 4 actions (`UPSELL`, `PRICE_REVIEW`, `DISCOUNT_REDUCTION`, `LOYALTY_OFFER`). Strictest integrity rules (never substitutes revenue for profit). |
| 3 | `purchase_trend` | Revenue direction. Largest single churn contribution (35 pts in the purchase group), feeds `growth_potential` (±30), `UPSELL`, and retention confidence. |
| 4 | `complaint_impact` | Unlocks the highest-impact action `SERVICE_RECOVERY` (business_impact 1.0) and **forbids** nearly every sales action while critical/unresolved; drives `relationship_health`. |
| 5 | `payment_behavior` | Cash-flow risk. Unlocks `CREDIT_REVIEW` / `PAYMENT_TERMS_REVIEW`, contributes to churn, and becomes the `payment_risk` state dimension. |
| 6 | `purchase_cycle` | Recency detection. Unlocks `REACTIVATION`; contributes to churn (up to 30 pts in the purchase group). |
| 7 | `share_of_wallet` | Wallet headroom. Largest single growth-potential weight (+40), unlocks `CROSS_SELL` / `VOLUME_OFFER`, and is a churn input. |
| 8 | `growth_potential` (derived) | The opportunity side. Gates `CROSS_SELL`, `VOLUME_OFFER`, `BUNDLE_OFFER`; only as strong as its weakest input. |
| 9 | `offer_affinity` | Personalization. Unlocks `BUNDLE_OFFER` / `DISCOUNT_REDUCTION`, nudges `relationship_health`, detects `OFFER_FATIGUE`. |
| 10 | `margin_trend` | Profitability *direction*; sharpens `PRICE_REVIEW` urgency. Smallest footprint of the core signals. |
| 11 | `dev_request` (auxiliary) | Grounding only: prevents `PRODUCT_DEVELOPMENT_FOLLOWUP` from firing without real open requests. Not one of the ten MVP signals. |

---

### 4.1 `profit` — Signal 1 (base) — ⭐ #2

**Question:** is this customer actually profitable?

**Computation:** `profit = revenue − product_cost − return_amount`; `margin = profit / revenue`.
Discounts are *not stored* on sales lines, so they are reported as `0` / `discount_available:
False` rather than invented. Cost comes from `realized_costs` joined on `Sales_Line_ID`.

**Classification (margin):** `high_profit ≥ 0.25` → positive · `normal_profit ≥ 0.10` →
neutral · `low_profit ≥ 0.00` → warning · `negative_profit < 0` → critical.

**Integrity gates:**
- No revenue / no orders → `unknown`, confidence 0.
- No cost data at all (`costed_revenue ≤ 0`) → `unknown` — **never** substitutes revenue for profit.
- Partial cost coverage: `coverage = costed_revenue / revenue`; if `coverage < 0.5` →
  `low_confidence`, `confidence = coverage` — the number is shown but flagged unreliable.

**Confidence:** `min(1.0, cost_coverage)`.

---

### 4.2 `purchase_trend` — Signal 2 (base) — ⭐ #3

**Question:** is the customer buying more or less than their own baseline?

**Computation:** recent 90-day revenue vs the *immediately preceding* 90-day revenue
(`pct_change`). Trend is always **relative to the customer's own history**, never an
absolute number.

**Classification (revenue change):** `strong_growth ≥ +30%` → positive · `growth ≥ +10%` →
positive · `decline ≤ −10%` → warning · `strong_decline ≤ −30%` → critical · else `stable`
(neutral). A `±10%` stable band avoids noise on tiny bases.

**Degradation:** no comparable previous period, or fewer than 3 total orders → `unknown`
with an explicit reason. **Confidence:** `min(1.0, total_orders / 10)` — more history, more
trust.

**Evidence** includes revenue/order/quantity change pct and both period values.

---

### 4.3 `payment_behavior` — Signal 3 (base) — ⭐ #5

**Question:** how reliable is the customer's payment, and is it getting worse?

**Computation (from `collections`):** median delay days, overdue ratio (late/total above
15 days), bounced cheques, and **deterioration** = recent 180-day avg delay − baseline
180-day avg delay (the customer's own pattern, not a global rule).

**Classification (median delay):** `excellent ≤ 7d` / `good ≤ 15d` → positive ·
`warning ≤ 30d` / `poor ≤ 45d` → warning · `> 45d` → critical.

**Direction:** `declining` when deterioration ≥ 10 days, `improving` when ≤ −10 days.
A marked deterioration escalates status even from a good base. **Confidence:**
`min(1.0, payments / 10)`.

**Evidence:** avg/median/max delay, overdue amount & ratio, bounced cheques, deterioration
days.

---

### 4.4 `share_of_wallet` — Signal 4 (base) — ⭐ #7

**Question:** how much of the customer's total spend do we capture?

**Computation:** `our_spend / estimated_total_spend` averaged over the trailing 3 months
from the **external** `wallet_share` estimates. Never reconstructed from our own sales
(that would be circular). No external estimate → `unknown`.

**Classification:** `high_share ≥ 0.65` → positive · `low_share ≤ 0.35` → neutral ·
`medium_share` → neutral. **Staleness:** if the newest month is > 365 days old, confidence
is capped at 0.4 and a reason is added. **Confidence:** `min(1.0, months / wallet_months)`.

**Evidence** includes `main_competitor` and `data_source` — useful for sales planning.

---

### 4.5 `purchase_cycle` — Signal 5 (base) — ⭐ #6

**Question:** is the customer overdue relative to *their* normal buying cadence?

**Computation:** `days_since_last_purchase / median inter-purchase gap` (robust median, not
a fragile average). Requires ≥ 3 distinct purchase dates.

**Classification (ratio):** `≥ 1.75` → severely_late (critical) · `≥ 1.25` →
significantly_late (warning) · `≥ 1.0` → slightly_late (neutral) · else normal (positive).

**Confidence:** `min(1.0, gaps / 8)`. **Evidence:** normal cycle days, days since last
purchase, deviation ratio, distinct purchases.

---

### 4.6 `margin_trend` — Signal 6 (base) — ⭐ #10

**Question:** is the customer's margin improving or eroding?

**Computation:** current 3-month margin vs previous 3-month margin, on **cost-matched**
sales lines only (margin needs revenue AND cost). `change = cur_margin − prev_margin`.

**Classification:** `improving ≥ +3pp` → positive · `strong_decline ≤ −10pp` → critical ·
`declining ≤ −3pp` → warning · else stable (neutral).

**Degradation:** missing cost-matched sales in either window → `unknown`. **Confidence:**
fixed at 0.8 when computed.

---

### 4.7 `growth_potential` — Signal 7 (derived) — ⭐ #8

**Question:** is additional business *plausible* here? (Opportunity, not forecast.)

**Deterministic weighted score** (every point backed by a real signal):

| Input | Contribution |
| --- | --- |
| `share_of_wallet` low | +40 (medium +15) |
| `purchase_trend` positive | +25 (neutral +10, warning/critical **−30**) |
| `payment_behavior` positive | +20 (warning/critical **−20**) |
| `profit` high/normal | +15 (negative **−25**) |

Score clamped to 0–100 → `high ≥ 60` (status positive) · `medium ≥ 35` (neutral) · `low`
(neutral). **Confidence = the *weakest* contributing signal's confidence** — never
overclaims.

---

### 4.8 `churn_risk` — Signal 8 (derived) — ⭐ #1

**Question:** how strong is the evidence the customer is drifting away?

**Deterministic grouped scoring** — correlated signals are **not** double-counted:

| Group | Contribution |
| --- | --- |
| **purchase** (trend + cycle, take the max) | trend critical 35 / warning 25 · cycle critical 30 / warning 20 |
| **complaint** (`complaint_impact` warning/critical) | 25 / 15 |
| **payment** | critical 15 · warning or declining 8 |
| **share** (low share of wallet) | 5 |

`total = min(100, Σ points)`; `strong_groups = count of groups with ≥ 15 points`.
Bands: `critical ≥ 4` strong groups · `high ≥ 3` · `warning ≥ 2` · else `low`/neutral.
**Confidence = weakest contributing signal** (irrelevant `unknown` signals never drag it
down). `evidence.contributions` lists each group, points, and reason — fully explainable.

---

### 4.9 `complaint_impact` — Signal 9 (base) — ⭐ #4

**Question:** what happened to purchases *after* the complaint?

**Computation:** revenue 90 days before vs 90 days after the most recent complaint
(observational — wording is association-based, never causal). Uses severity weights
(بحرانی 3.0 / زیاد 2.0 / متوسط 1.0 / کم 0.5) and unresolved statuses.

**Classification (revenue change):** `≤ −40%` → severe_decline (critical) · `≤ −20%` →
decline (warning) · `≥ 0` → no_decline (neutral) · else mild_decline (neutral). Escalates
to **critical** when unresolved complaints remain and severity ≥ 2.0 with a decline.
**Confidence:** `min(1.0, complaints / 3)`.

**Evidence:** complaint count, unresolved count, max severity, before/after revenue and
orders, days since complaint, recovery status.

---

### 4.10 `offer_affinity` — Signal 10 (base) — ⭐ #9

**Question:** which offer mechanism does the customer actually respond to?

**Computation:** acceptance rate per offer type from `offers` (قبول / رد), mapped to
`volume_offer`, `discount`, `payment_terms`. The preferred type = best response rate among
types with ≥ 3 decided responses (`min_sample`). Never infers a preference from fewer.

**Status:** `positive` if best rate ≥ 0.5 else `neutral`. No history → `unknown`.
**Confidence:** `min(1.0, preferred_total / 9)`. Drives `OFFER_FATIGUE` (rate < 0.5 with
≥ 3 responses) in the reason layer.

---

### 4.11 `dev_request` — auxiliary (base) — ⭐ #11

**Question:** are there open product-development requests?

**Computation:** count of dev requests in open statuses (درحال بررسی / درحال توسعه /
نمونه تأیید). `open ≥ 1` → positive with `confidence = min(1.0, open/2)`; else neutral.
Grounds the `PRODUCT_DEVELOPMENT_FOLLOWUP` action.

---

## 5. The State Layer — 6 Dimensions (`state/customer_state.py`)

`CustomerState` deliberately has **multiple dimensions, not one universal score**:

| Dimension | Derivation |
| --- | --- |
| `value` | Revenue scale `20·log10(revenue+1)` (0–100). high ≥ 70, medium ≥ 50, low. A trusted *negative profit* caps value to low/30 regardless of revenue. |
| `churn_risk` | Passthrough of the `churn_risk` signal. |
| `growth_opportunity` | Passthrough of the `growth_potential` signal. |
| `profitability` | Passthrough of `profit` (`low_confidence` → reported as `unknown`). |
| `payment_risk` | Inverse of `payment_behavior`: positive/neutral → low, warning → warning, critical → critical. |
| `relationship_health` | Base 50; complaint critical −30 / warning −15 / each unresolved −10; payment declining/warning/critical −10; offer affinity positive +5. Status: healthy ≥ 70 · warning ≥ 40 · poor. Confidence = weakest contributor. |

Each dimension carries `score, status, confidence, reasons, evidence` — the UI and chatbot
render these directly.

---

## 6. The Reason / Evidence Layer (`state/reason_engine.py`)

`build_reasons` produces **independently citable** `Reason` objects
(`reason_id`, `type`, `severity`, `confidence`, `evidence`, `source_signals`):

- `PURCHASE_DECLINING` (trend warning/critical)
- `PURCHASE_CYCLE_DELAYED` (cycle warning/critical)
- `PAYMENT_DETERIORATING` / `HIGH_CREDIT_RISK` (payment)
- `HIGH_PROFIT` / `LOW_MARGIN` (profit)
- `HIGH_GROWTH_POTENTIAL` (growth high)
- `COMPLAINT_FOLLOWED_BY_DECLINE` (complaint)
- `OFFER_FATIGUE` (affinity rate < 0.5, n ≥ 3)

Reasons are sorted by severity (critical → positive) so the most important lead. This is
the layer that lets the UI and the decision engine explain *why* without calling the LLM.

---

## 7. The Decision Engine — Next Best Action

### 7.1 The action catalog (`actions/definitions.py`)

15 declarative actions. Each declares `business_impact`, eligibility/forbidden conditions
(over signals *and* state), the signals that drive **urgency** and **confidence**, and a
suggested next step:

| Action | Category | Impact | Fires when | Forbidden when |
| --- | --- | --- | --- | --- |
| `SERVICE_RECOVERY` | quality | **1.0** | complaint critical/warning or unresolved | — |
| `RETENTION_CALL` | relationship | 0.9 | churn high/critical **and** value high/medium | — |
| `CROSS_SELL` | sales | 0.8 | growth positive, churn low/neutral, rel. healthy/warning | complaint critical/unresolved |
| `REACTIVATION` | sales | 0.8 | purchase cycle critical | — |
| `CREDIT_REVIEW` | collection | 0.8 | payment critical | — |
| `UPSELL` | sales | 0.7 | trend positive/neutral, profit positive/neutral | complaint critical |
| `PRICE_REVIEW` | commercial | 0.7 | profit warning/critical | — |
| `ACCOUNT_REVIEW` | relationship | 0.6 | relationship_health poor/warning | — |
| `DISCOUNT_REDUCTION` | commercial | 0.6 | profit warning/critical + affinity positive | — |
| `PAYMENT_TERMS_REVIEW` | commercial | 0.6 | payment warning | payment critical |
| `VOLUME_OFFER` | sales | 0.6 | share neutral/positive + growth positive | complaint critical |
| `PRODUCT_DEVELOPMENT_FOLLOWUP` | relationship | 0.5 | open dev requests ≥ 1 | — |
| `LOYALTY_OFFER` | sales | 0.5 | value high, churn low/neutral, rel. healthy | complaint critical |
| `BUNDLE_OFFER` | sales | 0.4 | affinity positive + churn low/neutral | complaint critical |
| `NO_ACTION` | attention | 0.0 | fallback when nothing else is eligible | — |

### 7.2 Eligibility (`actions/eligibility.py`)

Conditions are **data structures, not scattered if/else**:

```text
{"signal": id, "status": [...]}            signal.status in [...]
{"signal": id, "score_ge": n}              signal.score >= n
{"signal": id, "evidence_ge": {k: n}}      signal.evidence[k] >= n
{"state": dim, "status": [...]}            state.dim.status in [...]
{"state": dim, "score_ge": n}              state.dim.score >= n
```

- A group matches when every `all` condition holds **and** at least one `any` condition
  holds (empty lists are trivially satisfied).
- **Forbidden always wins** — e.g. a critical/unresolved complaint blocks every sales
  action, because you must not sell to a customer you haven't made whole yet.

### 7.3 Ranking (`actions/ranking.py`)

```text
priority = business_impact × urgency × confidence × data_quality
```

- **business_impact** — declared per action (0.0–1.0).
- **urgency** — max of `_STATUS_URGENCY` over the action's `urgency_signals`
  (critical 1.0 · warning 0.7 · positive 0.6 · neutral 0.3 · unknown 0.1; state statuses
  high/poor 0.8 · medium 0.5 · low/healthy 0.2). Default 0.3.
- **confidence** — **min** of the `confidence_signals` (the weakest link; default 0.5).
- **data_quality** — mean confidence across all signals, clamped 0–1.

Multiplicative, so a single low-confidence or low-quality input visibly lowers priority —
the engine refuses to overclaim.

### 7.4 The NBA pipeline (`actions/next_best_action.py`)

`recommend(signals, state, data_quality, limit)`:

1. Evaluate every action → `eligible` list, plus which actions were **blocked by forbidden**
   conditions (surfaced to the UI as `blocked_actions`).
2. If nothing is eligible → honest fallback `NO_ACTION` ("Monitor only") — never a
   made-up action.
3. Rank by `(−priority, action_id)`; return **top 3** (configurable `limit`).
4. Each recommended action carries a deterministic `reason` (first reason of its urgency
   signals), `evidence` (deduplicated signal reasons), `suggested_next_step`, and
   `blocked_actions`.

---

## 8. Portfolio-Level: At-Risk Ranking (`at_risk.py`)

`engine_at_risk(limit)` ranks the whole portfolio by the **real** `churn_risk` signal —
never a hand-written SQL heuristic. For every customer it computes only the base signals
churn risk actually consumes (trend, cycle, payment, share of wallet, complaint impact),
derives the real churn score, and sorts by `(−risk_score, −revenue)` so big accounts win
ties. Results are **cached under the global data fingerprint** — one full computation,
instant reads afterwards (see `cache.py`). A broken customer never aborts the pass.

---

## 9. Caching (`cache.py`)

- Plain-JSON cache under `<repo>/data/cache/<kind>/<key>.json`.
- Invalidated automatically: the caller stores a **fingerprint** of the deterministic data
  payload (`SCHEMA_VERSION` + row counts + newest dates); any data change produces a new
  fingerprint and a recompute.
- Atomic writes (temp file + rename) so concurrent readers never see a half-written file.
- Used by: at-risk ranking, dashboard intelligence, LLM summaries, next-action text.

---

## 10. Data Quality (`service._data_quality`)

`DataQuality(overall, warnings)`:
- `overall` = mean confidence over all signals.
- `warnings` — cost data covers only X% of revenue; wallet-share estimate stale (> 1 year);
  some signals low-confidence (small sample).

`overall` feeds directly into action priority, so **untrustworthy data automatically
depresses recommendations**.

---

## 11. The LLM Boundary — Tools, MCP, Agents

The engine's output reaches the LLM only through **read-only tools** (JSON strings);
`backend/crm/tools.py` and `backend/mcp/duckdb_server.py` expose:

- `get_customer_signals` — all signals for one customer
- `get_customer_state` — the 6 state dimensions
- `get_customer_reasons` — structured evidence/why
- `get_next_best_actions` — eligible + ranked actions **only** (LLM may never invent one)
- `get_customer_action_plan` — complete deterministic context (state + reasons + actions + quality)
- `top_at_risk_customers` — real churn-signal ranking for "who is at risk" questions

Agents (`backend/agents/db_agent.py`, `intel_summary.py`, `recommend.py`) are instructed in
hard rules: *never invent a signal, score, threshold, or action; never recalculate; only
explain/personalize*. `backend/crm/labels.py` translates canonical English reasons to plain
Persian at the API boundary (dashboard, 360 view, analyses, LLM summary).

---

## 12. ⭐ Importance Priority — Engine Components

If you must invest effort, in this order:

1. **Signal correctness & integrity** (`signals/`, `data.py`) — the whole system inherits
   its truth from here. Wrong or overclaimed signals corrupt state, reasons, and actions.
2. **Eligibility + forbidden rules** (`actions/eligibility.py`, `definitions.py`) — these
   decide *what the user is told to do*, including the critical "don't sell to an
   unresolved-complaint customer" safety gates.
3. **Ranking formula** (`actions/ranking.py`) — priority = impact × urgency × confidence ×
   quality; tune weights/urgency maps before touching anything else in the action layer.
4. **State dimensions** (`state/customer_state.py`) — the human-readable summary that the
   UI and summaries are built on.
5. **Reason/evidence layer** (`state/reason_engine.py`) — explainability and the
   deterministic "why" for every recommendation.
6. **Central config** (`config.py`) — keep every threshold here; tune, don't hard-code.
7. **Data-quality assessment** (`service._data_quality`) — trust gating; low quality must
   visibly lower priorities.
8. **Caching** (`cache.py`, `at_risk.py`) — performance; correctness of invalidation
   matters more than speed.
9. **LLM tool surface & guards** (`tools.py`, `mcp/duckdb_server.py`, agent prompts) —
   safety boundary; cheap to break, so guardrails are non-negotiable.
10. **Persian labels/translation** (`labels.py`) — localization; only user-facing polish.

---

## 13. How to Extend

**Add a signal** (1) implement `calculate` following an existing module's contract, (2)
register it in `signals/__init__.py` (base or derived), (3) add thresholds to `config.py`,
(4) add a Persian label in `labels.py`, (5) wire it into state/reasons/actions where it
belongs, (6) add a test.

**Add an action** (1) add a declarative `_def(...)` in `actions/definitions.py` with
eligibility/forbidden conditions and urgency/confidence signals, (2) pick `business_impact`,
(3) add Persian labels in `labels.py`. No ranking code changes needed — the catalog is
data-driven.

**Change a threshold** — edit `backend/crm/config.py` only; the calculation logic never
changes.
