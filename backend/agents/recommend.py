"""Deterministic recommendation signals.

The copilot is expected to close every answer with a concrete, defensible
recommendation ("sell product X, roughly N units, on credit vs cash, now vs
later"). Asking the LLM to *think of* those angles does not work reliably: it
falls back to generic advice a reader could have written without seeing any
data ("offer them attractive discounts").

So the angles the business actually cares about are computed HERE, in SQL,
and handed to the prompt as measured facts:

* headroom      - how much more of their spend we could win (wallet_share)
* cadence       - how often they buy, and whether they are overdue
* basket        - what they buy and in what typical volume
* open issues   - unresolved complaints / development requests to check first
* payment terms - cash vs credit, from how they actually pay
* collection    - how fast they settle, and any bounced cheques

Each signal degrades independently: a failing or empty query is skipped
rather than breaking the answer.
"""
from __future__ import annotations

import re
from typing import Any, Awaitable, Callable

# Statuses that mean "still open, somebody should look at this".
OPEN_COMPLAINT_STATUSES = ("نیازمند بررسی", "درحال بررسی")
OPEN_REQUEST_STATUSES = ("درحال بررسی", "درحال توسعه")

# A customer id we are willing to interpolate into SQL. Anything that doesn't
# match is rejected outright rather than escaped — these ids are model output,
# so the safe move is a strict allowlist.
_SAFE_ID = re.compile(r"^[A-Za-z0-9_-]{1,32}$")

RunSql = Callable[[str], Awaitable[dict[str, Any]]]


def _quoted(values: tuple[str, ...]) -> str:
    return ", ".join("'" + v.replace("'", "''") + "'" for v in values)


def _rows(data: dict[str, Any]) -> list[list[Any]]:
    if not data or data.get("error"):
        return []
    return data.get("rows") or []


def _fmt(v: Any, digits: int = 1) -> str:
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return f"{v:,.{digits}f}".rstrip("0").rstrip(".") if digits else f"{v:,.0f}"
    return str(v)


def _headroom_sql(cid: str) -> str:
    # Latest month we have an estimate for; that month's gap is the opportunity.
    return f"""
SELECT Month_Key, Estimated_Total_Purchase, Nafis_Purchase,
       Estimated_Total_Purchase - Nafis_Purchase AS gap,
       ROUND(Nafis_Purchase * 100.0 / NULLIF(Estimated_Total_Purchase, 0), 1) AS our_share_pct,
       Main_Competitor
FROM wallet_share WHERE Customer_ID = '{cid}'
ORDER BY Month_Key DESC LIMIT 1"""


def _cadence_sql(cid: str) -> str:
    return f"""
WITH d AS (SELECT DISTINCT CAST("تاریخ" AS DATE) dt FROM sales WHERE Customer_ID = '{cid}')
SELECT COUNT(*) AS order_days,
       ROUND(DATE_DIFF('day', MIN(dt), MAX(dt)) * 1.0 / NULLIF(COUNT(*) - 1, 0), 1) AS avg_days_between,
       MAX(dt) AS last_purchase,
       DATE_DIFF('day', MAX(dt), (SELECT MAX(CAST("تاریخ" AS DATE)) FROM sales)) AS days_since_last
FROM d"""


def _basket_sql(cid: str) -> str:
    return f"""
SELECT Product_ID, SUM("مقدار") AS units, ROUND(AVG("مقدار"), 1) AS avg_units_per_line,
       COUNT(DISTINCT "شماره فاکتور") AS orders
FROM sales WHERE Customer_ID = '{cid}'
GROUP BY 1 ORDER BY units DESC LIMIT 5"""


def _open_complaints_sql(cid: str) -> str:
    return f"""
SELECT Complaint_Status, COUNT(DISTINCT Complaint_ID) AS n
FROM complaints WHERE Customer_ID = '{cid}'
  AND Complaint_Status IN ({_quoted(OPEN_COMPLAINT_STATUSES)})
GROUP BY 1 ORDER BY n DESC"""


def _open_requests_sql(cid: str) -> str:
    return f"""
SELECT Status, COUNT(DISTINCT Request_ID) AS n
FROM dev_requests WHERE Customer_ID = '{cid}'
  AND Status IN ({_quoted(OPEN_REQUEST_STATUSES)})
GROUP BY 1 ORDER BY n DESC"""


def _payment_mix_sql(cid: str) -> str:
    return f"""
SELECT "نوع پرداخت" AS payment_type, COUNT(*) AS lines,
       ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) AS pct
FROM sales WHERE Customer_ID = '{cid}'
GROUP BY 1 ORDER BY lines DESC"""


def _collection_sql(cid: str) -> str:
    return f"""
SELECT COUNT(*) AS events, ROUND(AVG("روز تأخیر"), 1) AS avg_delay_days,
       MAX("روز تأخیر") AS worst_delay_days,
       SUM(CASE WHEN "چک برگشتی" = 'بله' THEN 1 ELSE 0 END) AS bounced_cheques
FROM collections WHERE Customer_ID = '{cid}'"""


# --- product-side SQL ------------------------------------------------------
# Note: avoid `cost`, `range`, `sample` etc. as aliases — they are DuckDB
# reserved words and fail to parse.


def _demand_trend_sql(pid: str) -> str:
    return f"""
SELECT strftime(CAST("تاریخ" AS DATE), '%Y') AS yr, SUM("مقدار") AS units,
       COUNT(DISTINCT Customer_ID) AS buyers
FROM sales WHERE Product_ID = '{pid}'
GROUP BY 1 ORDER BY 1 DESC LIMIT 4"""


def _margin_sql(pid: str) -> str:
    return f"""
SELECT ROUND(AVG(s."قیمت فی فروش"), 1) AS avg_price,
       ROUND(AVG(rc."هزینه کل به ازای واحد"), 1) AS unit_cost,
       ROUND((AVG(s."قیمت فی فروش") - AVG(rc."هزینه کل به ازای واحد"))
             * 100.0 / NULLIF(AVG(s."قیمت فی فروش"), 0), 1) AS margin_pct
FROM sales s JOIN realized_costs rc ON s.Sales_Line_ID = rc.Sales_Line_ID
WHERE s.Product_ID = '{pid}'"""


def _offer_response_sql(pid: str) -> str:
    return f"""
SELECT Result, COUNT(*) AS n, ROUND(AVG(Offer_Discount_Pct) * 100, 2) AS avg_discount_pct
FROM offers WHERE Product_ID = '{pid}'
GROUP BY 1 ORDER BY n DESC"""


def _whitespace_sql(pid: str) -> str:
    """Customers buying this product's family but not this product — the
    clearest cross-sell list we can produce."""
    return f"""
WITH fam AS (SELECT "گروه کالا" AS g FROM products WHERE Product_ID = '{pid}' LIMIT 1),
buyers AS (SELECT DISTINCT Customer_ID FROM sales WHERE Product_ID = '{pid}'),
fam_buyers AS (
    SELECT DISTINCT s.Customer_ID FROM sales s
    JOIN products p ON s.Product_ID = p.Product_ID
    WHERE p."گروه کالا" = (SELECT g FROM fam)
)
SELECT COUNT(*) AS prospects FROM fam_buyers
WHERE Customer_ID NOT IN (SELECT Customer_ID FROM buyers)"""


def _top_buyers_sql(pid: str) -> str:
    return f"""
SELECT Customer_ID, SUM("مقدار") AS units,
       ROUND(SUM("مقدار") * 100.0 / SUM(SUM("مقدار")) OVER (), 1) AS pct_of_product
FROM sales WHERE Product_ID = '{pid}'
GROUP BY 1 ORDER BY units DESC LIMIT 3"""


def _product_quality_sql(pid: str) -> str:
    return f"""
SELECT (SELECT COUNT(DISTINCT Complaint_ID) FROM complaints WHERE Product_ID = '{pid}') AS complaints,
       (SELECT COUNT(DISTINCT Sales_Line_ID) FROM sales WHERE Product_ID = '{pid}') AS sales_lines,
       (SELECT COUNT(DISTINCT Request_ID) FROM dev_requests
        WHERE Product_ID = '{pid}' AND Status IN ({_quoted(OPEN_REQUEST_STATUSES)})) AS open_requests"""


async def product_signals(product_id: str, run_sql: RunSql) -> str:
    """Compute the recommendation signals for one product.

    Mirrors ``customer_signals`` but answers the product-side questions: is
    demand growing, how much discount room does the margin allow, what
    discount level actually closes, and who could we sell it to next.
    """
    pid = (product_id or "").strip()
    if not _SAFE_ID.match(pid):
        return ""

    lines: list[str] = []
    must: list[str] = []

    async def fetch(sql: str) -> list[list[Any]]:
        try:
            return _rows(await run_sql(sql))
        except Exception:  # noqa: BLE001 - a dead signal must not sink the answer
            return []

    # --- demand trend: is this product growing or dying? -----------------
    trend = await fetch(_demand_trend_sql(pid))
    if trend:
        series = "; ".join(
            f"{r[0]}: {_fmt(r[1], 0)} units / {_fmt(r[2], 0)} buyers" for r in trend
        )
        direction = ""
        if len(trend) >= 2:
            newest, prev = trend[0][1], trend[1][1]
            if isinstance(newest, (int, float)) and isinstance(prev, (int, float)) and prev:
                change = (newest - prev) * 100.0 / prev
                direction = (
                    f" Latest year is {_fmt(abs(change))}% "
                    f"{'DOWN' if change < 0 else 'UP'} on the previous year."
                )
        lines.append(f"- DEMAND BY YEAR (newest first): {series}.{direction}")

    # --- margin: how much discount room actually exists ------------------
    for r in await fetch(_margin_sql(pid)):
        price, unit_cost, margin = (list(r) + [None] * 3)[:3]
        if price and unit_cost:
            room = ""
            if isinstance(margin, (int, float)):
                room = (
                    " Margin is thin — discounting further erodes it; sell on "
                    "value/volume instead of price."
                    if margin < 15
                    else " There is room to discount if needed."
                )
            lines.append(
                f"- MARGIN: average selling price {_fmt(price)} vs unit cost "
                f"{_fmt(unit_cost)} -> {_fmt(margin)}% margin.{room}"
            )
            if margin is not None:
                must.append(f"margin {_fmt(margin)}%")

    # --- what discount actually closes a deal ----------------------------
    offers = await fetch(_offer_response_sql(pid))
    if offers:
        detail = "; ".join(
            f"{r[0]}: {_fmt(r[1], 0)} offers at avg {_fmt(r[2])}% discount" for r in offers
        )
        accepted = next((r for r in offers if str(r[0]).strip() == "قبول"), None)
        total = sum(r[1] or 0 for r in offers)
        note = ""
        if accepted and total:
            rate = (accepted[1] or 0) * 100.0 / total
            note = (
                f" Accept rate {_fmt(rate)}%; accepted offers averaged "
                f"{_fmt(accepted[2])}% discount."
            )
            must.append(f"~{_fmt(accepted[2])}% discount (the level that closes)")
        lines.append(f"- OFFER HISTORY: {detail}.{note}")

    # --- cross-sell whitespace: who to approach next ---------------------
    for r in await fetch(_whitespace_sql(pid)):
        prospects = r[0] if r else None
        if prospects:
            lines.append(
                f"- CROSS-SELL WHITESPACE: {_fmt(prospects, 0)} customers already buy "
                "this product's family but have never bought THIS product — the "
                "readiest prospect list."
            )
            must.append(f"{_fmt(prospects, 0)} untapped same-family customers")

    # --- concentration risk ----------------------------------------------
    buyers = await fetch(_top_buyers_sql(pid))
    if buyers:
        detail = "; ".join(f"{r[0]} ({_fmt(r[2])}%)" for r in buyers)
        top_share = buyers[0][2] if buyers[0][2] is not None else 0
        risk = (
            " Highly concentrated — losing the top buyer would hit this product hard."
            if isinstance(top_share, (int, float)) and top_share > 40
            else ""
        )
        lines.append(f"- TOP BUYERS: {detail}.{risk}")

    # --- quality / open requests -----------------------------------------
    for r in await fetch(_product_quality_sql(pid)):
        complaints, sales_lines, open_reqs = (list(r) + [None] * 3)[:3]
        if sales_lines:
            rate = (complaints or 0) * 1000.0 / sales_lines
            lines.append(
                f"- COMPLAINTS: {_fmt(complaints, 0)} on {_fmt(sales_lines, 0)} sales "
                f"lines ({_fmt(rate)} per 1000 lines)."
            )
        if open_reqs:
            lines.append(
                f"- OPEN DEVELOPMENT REQUESTS on this product: {_fmt(open_reqs, 0)} "
                "awaiting our response."
            )

    if not lines:
        return ""

    return (
        "\nMeasured recommendation signals for this product (computed exactly "
        "from the full data — build the closing recommendation on THESE, not on "
        "generic advice):\n" + "\n".join(lines) + _must_mention_block(must)
    )


def _must_mention_block(must: list[str]) -> str:
    """Force the specific literals into the answer.

    Even with the numbers in front of it, the model often drops the concrete
    ones (the competitor's name, the volume to offer) and falls back to vague
    phrasing. Listing them explicitly as required tokens fixes that.
    """
    items = [m for m in dict.fromkeys(must) if m]
    if not items:
        return ""
    return (
        "\nThese exact values MUST appear in your recommendation "
        "(they are what makes it actionable): " + " | ".join(items)
    )


async def customer_signals(customer_id: str, run_sql: RunSql) -> str:
    """Compute the recommendation signals for one customer.

    Returns a plain-text block of measured facts for the prompt, or "" when
    nothing could be computed (unknown customer, all queries failed).
    """
    cid = (customer_id or "").strip()
    if not _SAFE_ID.match(cid):
        return ""

    lines: list[str] = []
    must: list[str] = []

    async def fetch(sql: str) -> list[list[Any]]:
        try:
            return _rows(await run_sql(sql))
        except Exception:  # noqa: BLE001 - one dead signal must not sink the answer
            return []

    # --- headroom: the single most actionable number we have -------------
    for r in await fetch(_headroom_sql(cid)):
        month, est, ours, gap, share, competitor = (list(r) + [None] * 6)[:6]
        if est:
            lines.append(
                f"- HEADROOM (as of {month}): their estimated total spend is {_fmt(est)}, "
                f"we supply {_fmt(ours)} ({_fmt(share)}% share) -> untapped gap {_fmt(gap)}. "
                f"Main competitor: {competitor}."
            )
            if competitor:
                must.append(f"competitor '{competitor}' (holds the gap)")
            if gap:
                must.append(f"untapped gap {_fmt(gap)}")

    # --- cadence: when to approach them ----------------------------------
    for r in await fetch(_cadence_sql(cid)):
        days, gap_days, last, since = (list(r) + [None] * 4)[:4]
        if days and gap_days:
            overdue = ""
            if isinstance(since, (int, float)) and isinstance(gap_days, (int, float)):
                overdue = (
                    f" That is {_fmt(since / gap_days)}x their normal gap - overdue."
                    if since > gap_days * 1.5
                    else " That is within their normal rhythm."
                )
            lines.append(
                f"- CADENCE: buys on {days} distinct days, on average every "
                f"{_fmt(gap_days)} days. Last purchase {last}, {_fmt(since)} days "
                f"before the latest data.{overdue}"
            )

    # --- basket: what and how much to offer ------------------------------
    basket = await fetch(_basket_sql(cid))
    if basket:
        top = "; ".join(
            f"{r[0]} ({_fmt(r[1])} units over {_fmt(r[3], 0)} orders, "
            f"typically {_fmt(r[2])}/line)"
            for r in basket[:3]
        )
        lines.append(f"- BUYS MOST: {top}")
        # A concrete volume to propose, anchored on how they actually order.
        if basket[0][0] and basket[0][2]:
            must.append(
                f"offer ~{_fmt(basket[0][2])} units of {basket[0][0]} "
                "(their typical order size)"
            )

    # --- open issues: must be checked before selling ---------------------
    complaints = await fetch(_open_complaints_sql(cid))
    if complaints:
        detail = ", ".join(f"{r[0]}: {_fmt(r[1], 0)}" for r in complaints)
        lines.append(
            f"- OPEN COMPLAINTS (unresolved, check before pushing a new offer): {detail}"
        )
    else:
        lines.append("- OPEN COMPLAINTS: none outstanding.")

    requests = await fetch(_open_requests_sql(cid))
    if requests:
        detail = ", ".join(f"{r[0]}: {_fmt(r[1], 0)}" for r in requests)
        lines.append(
            f"- OPEN DEVELOPMENT REQUESTS (awaiting our response): {detail}"
        )

    # --- payment preference ----------------------------------------------
    mix = await fetch(_payment_mix_sql(cid))
    if mix:
        detail = ", ".join(f"{r[0]} {_fmt(r[2])}%" for r in mix)
        lines.append(f"- HOW THEY PAY: {detail}")

    # --- collection behaviour: cash vs credit decision --------------------
    for r in await fetch(_collection_sql(cid)):
        events, avg_delay, worst, bounced = (list(r) + [None] * 4)[:4]
        if events:
            risk = ""
            if bounced:
                risk = f" {_fmt(bounced, 0)} bounced cheque(s) on record - credit risk."
            lines.append(
                f"- COLLECTION: {_fmt(events, 0)} settlements, average "
                f"{_fmt(avg_delay)} days late (worst {_fmt(worst, 0)}).{risk}"
            )

    if not lines:
        return ""

    return (
        "\nMeasured recommendation signals for this customer (computed exactly "
        "from the full data — build the closing recommendation on THESE, not on "
        "generic advice):\n" + "\n".join(lines) + _must_mention_block(must)
    )
