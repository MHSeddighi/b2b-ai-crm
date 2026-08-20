"""Real-data read API for the frontend (Dashboard, Customers, Customer 360).

These endpoints query the DuckDB database directly (read-only, no LLM) so the
frontend can render live numbers instead of mock data. All values are computed
from the real tables; nothing is fabricated.
"""
from __future__ import annotations

from typing import Any

import duckdb

from backend.config import settings

_MONTHS_FA = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
              "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"]


def _connect() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(str(settings.db_path), read_only=True)
    con.execute("SET enable_external_access=false")
    return con


def _fa_month(ym: str) -> str:
    """Map 'YYYY-MM' to a short Persian label (e.g. '2020-01' -> 'دی 99')."""
    try:
        year, month = ym.split("-")
        m = _MONTHS_FA[int(month) - 1]
        return f"{m} {int(year) % 100}"
    except Exception:  # noqa: BLE001
        return ym


def _rows(con: duckdb.DuckDBPyConnection, sql: str) -> list[tuple]:
    return con.execute(sql).fetchall()


def dashboard() -> dict[str, Any]:
    con = _connect()
    try:
        total_customers = _rows(con, 'SELECT COUNT(*) FROM customers')[0][0]
        total_orders = _rows(con, 'SELECT COUNT(DISTINCT "شماره فاکتور") FROM sales')[0][0]
        total_revenue = _rows(con, 'SELECT SUM("مبلغ کل") FROM sales')[0][0] or 0
        total_complaints = _rows(con, 'SELECT COUNT(*) FROM complaints')[0][0]

        kpis = [
            {"label": "کل مشتریان", "value": total_customers,
             "change": None, "trend": "neutral"},
            {"label": "درآمد کل", "value": round(total_revenue),
             "change": None, "trend": "neutral"},
            {"label": "سفارش‌ها", "value": total_orders,
             "change": None, "trend": "neutral"},
            {"label": "شکایات", "value": total_complaints,
             "change": None, "trend": "neutral"},
        ]

        purchase_rows = _rows(con, """
            SELECT substr("تاریخ",1,7) AS m, SUM("مبلغ کل") AS v
            FROM sales GROUP BY 1 ORDER BY 1
        """)
        # last 24 months
        purchase_rows = purchase_rows[-24:]
        purchase_trend = [
            {"month": _fa_month(m), "value": round(v)} for m, v in purchase_rows
        ]

        complaint_rows = _rows(con, """
            SELECT substr(Created_At,1,7) AS m, COUNT(*) AS v
            FROM complaints GROUP BY 1 ORDER BY 1
        """)
        complaint_trend = [
            {"month": _fa_month(m), "value": v} for m, v in complaint_rows[-24:]
        ]

        segment_rows = _rows(con, """
            SELECT Customer_Segment, COUNT(*) FROM customers GROUP BY 1 ORDER BY 2 DESC
        """)
        segment_distribution = [
            {"name": s or "نامشخص", "value": c} for s, c in segment_rows
        ]

        status_rows = _rows(con, """
            SELECT Customer_Status, COUNT(*) FROM customers GROUP BY 1 ORDER BY 2 DESC
        """)
        status_distribution = [
            {"name": s or "نامشخص", "value": c} for s, c in status_rows
        ]
        return {
            "kpis": kpis,
            "purchaseTrend": purchase_trend,
            "complaintTrend": complaint_trend,
            "segmentDistribution": segment_distribution,
            "statusDistribution": status_distribution,
            "intelligence": _dashboard_intelligence(con),
            "recommendations": _income_recommendations(con),
        }
    finally:
        con.close()


def _dashboard_intelligence(con: duckdb.DuckDBPyConnection) -> dict[str, Any]:
    """Deterministic portfolio intelligence for the dashboard: at-risk revenue,
    complaint themes, offer effectiveness, collection risk and win-back
    opportunities. The LLM summary (cached) is layered on top separately.
    """
    ref = date_ref()
    ref_lit = f"DATE '{ref.isoformat()}'"

    # At-risk ranking comes from the real signal engine (cached), never from a
    # hand-written heuristic.
    from backend.crm.at_risk import engine_at_risk
    at_risk_rows = engine_at_risk(12)
    at_risk_count = len(at_risk_rows)
    at_risk_revenue = sum(r["revenue"] or 0 for r in at_risk_rows)

    themes = con.execute("""
        SELECT Complaint_Title, COUNT(*) AS v
        FROM complaints GROUP BY 1 ORDER BY v DESC, Complaint_Title LIMIT 6
    """).fetchall()

    offers = con.execute("""
        SELECT Offer_Type,
               COUNT(*) AS n,
               SUM(CASE WHEN Result = 'قبول' THEN 1 ELSE 0 END) AS accepted
        FROM offers GROUP BY 1
        HAVING COUNT(*) >= 5
        ORDER BY accepted * 1.0 / COUNT(*) DESC, Offer_Type
    """).fetchall()
    offer_eff = [
        {"type": t, "rate": (a / n) if n else 0, "count": n}
        for t, n, a in offers
    ]

    overdue = con.execute("""
        SELECT COALESCE(SUM("مبلغ وصول"), 0),
               COUNT(*) FILTER (WHERE "چک برگشتی" = 'بله')
        FROM collections WHERE "روز تأخیر" > 0
    """).fetchone()

    winback = con.execute(f"""
        WITH agg AS (
          SELECT c.Customer_ID,
            (SELECT MAX(CAST(s."تاریخ" AS DATE)) FROM sales s
              WHERE s.Customer_ID = c.Customer_ID) AS last_purchase,
            (SELECT COALESCE(SUM(s."مبلغ کل"), 0) FROM sales s
              WHERE s.Customer_ID = c.Customer_ID) AS revenue
          FROM customers c
        )
        SELECT COUNT(*), COALESCE(SUM(revenue), 0)
        FROM agg
        WHERE last_purchase IS NOT NULL
          AND last_purchase < {ref_lit} - INTERVAL 365 DAY
    """).fetchone()

    seg_rev = con.execute("""
        SELECT COALESCE(c.Customer_Segment, 'نامشخص'),
               COALESCE(SUM(s."مبلغ کل"), 0) AS v
        FROM customers c
        LEFT JOIN sales s ON c.Customer_ID = s.Customer_ID
        GROUP BY 1 ORDER BY v DESC, 1
    """).fetchall()

    return {
        "at_risk": {
            "count": at_risk_count,
            "revenue": round(at_risk_revenue),
            "top": at_risk_rows,
        },
        "complaint_themes": [
            {"name": t, "count": c} for t, c in themes
        ],
        "offer_effectiveness": offer_eff,
        "collection_risk": {
            "overdue": round(overdue[0] or 0),
            "bounced": overdue[1] or 0,
        },
        "winback": {
            "count": winback[0] or 0,
            "revenue": round(winback[1] or 0),
        },
        "segment_share": [
            {"name": s, "value": round(v)} for s, v in seg_rev
        ],
    }


def _income_recommendations(con: duckdb.DuckDBPyConnection) -> list[dict[str, Any]]:
    """Deterministic recommendations for better income, in plain Persian.
    Every item is computed from real data; nothing is invented."""
    intel = _dashboard_intelligence(con)
    recs: list[dict[str, Any]] = []
    at = intel["at_risk"]
    if at["count"]:
        recs.append({
            "id": "retain-at-risk",
            "tone": "negative",
            "title": "حفظ مشتریان در معرض از دست رفتن",
            "detail": (
                f"{at['count']} مشتری با مجموع درآمد {at['revenue']:,.0f} تومان "
                "در وضعیت نگران‌کننده‌اند؛ پیگیری تلفنی و رسیدگی به شکایت‌های باز "
                "اولویت اول است."),
            "impact": at["revenue"],
        })
    wb = intel["winback"]
    if wb["count"]:
        recs.append({
            "id": "winback",
            "tone": "positive",
            "title": "بازگرداندن مشتریان قدیمی",
            "detail": (
                f"{wb['count']} مشتری ارزشمند بیش از یک سال است خریدی نداشته‌اند "
                f"(مجموع درآمد سابق {wb['revenue']:,.0f} تومان)؛ یک پیشنهاد ویژه "
                "می‌تواند آن‌ها را برگرداند."),
            "impact": wb["revenue"],
        })
    if intel["complaint_themes"]:
        t = intel["complaint_themes"][0]
        recs.append({
            "id": "complaint-theme",
            "tone": "warning",
            "title": f"رسیدگی به «{t['name']}»",
            "detail": (
                f"این موضوع با {t['count']} شکایت پرتکرارترین مشکل است؛ رفع آن "
                "ریشه‌ای، جلوی از دست رفتن فروش را می‌گیرد."),
            "impact": 0,
        })
    if intel["offer_effectiveness"]:
        best = intel["offer_effectiveness"][0]
        recs.append({
            "id": "offer-type",
            "tone": "positive",
            "title": "تمرکز پیشنهادها روی نوع مؤثر",
            "detail": (
                f"پیشنهادهای «{best['type']}» بالاترین پذیرش را دارند "
                f"({round(best['rate'] * 100)}٪ از {best['count']} پیشنهاد)؛ "
                "تخصیص تخفیف به همین نوع، بازدهی بیشتری دارد."),
            "impact": 0,
        })
    col = intel["collection_risk"]
    if col["overdue"] or col["bounced"]:
        recs.append({
            "id": "collection",
            "tone": "warning",
            "title": "وصول مطالبات عقب‌افتاده",
            "detail": (
                f"{col['overdue']:,.0f} تومان مطالبات با تأخیر و "
                f"{col['bounced']} چک برگشتی ثبت شده؛ پیگیری وصول نقدینگی را "
                "افزایش می‌دهد."),
            "impact": col["overdue"],
        })
    return recs


def analyses() -> dict[str, Any]:
    """Real, computed payloads for the Analyses page (no LLM involved).

    Cached under the global data fingerprint: first visit computes, later
    visits read instantly until the underlying data changes."""
    from backend.crm import cache as store
    from backend.crm import data as crm_data
    con = _connect()
    try:
        fp = crm_data.global_fingerprint(con)
    finally:
        con.close()
    return store.cached("analyses", "overview",
                        _analyses_compute, fp)


def _analyses_compute() -> dict[str, Any]:
    con = _connect()
    try:
        ref = date_ref()
        ref_lit = f"DATE '{ref.isoformat()}'"

        # At-risk accounts ranked by the real signal engine (cached).
        from backend.crm.at_risk import engine_at_risk
        at_risk = [
            {
                "customer": r["customer_id"],
                "segment": r["segment"],
                "status": r["status"],
                "complaints": r["complaints"],
                "orders": r["orders"],
                "revenue": r["revenue"],
                "last_purchase": r["last_purchase"],
                "days_since": r["days_since"],
                "bounced": r["bounced"],
                "risk_level": r["risk_level"],
            }
            for r in engine_at_risk(15)
        ]

        themes = con.execute("""
            SELECT Complaint_Title, COUNT(*) AS v
            FROM complaints GROUP BY 1 ORDER BY v DESC, Complaint_Title LIMIT 8
        """).fetchall()
        complaint_themes = [
            {"name": t, "count": c} for t, c in themes
        ]

        seg_rev = con.execute("""
            SELECT COALESCE(c.Customer_Segment, 'نامشخص'),
                   COALESCE(SUM(s."مبلغ کل"), 0) AS v,
                   COUNT(DISTINCT c.Customer_ID) AS n
            FROM customers c
            LEFT JOIN sales s ON c.Customer_ID = s.Customer_ID
            GROUP BY 1 ORDER BY v DESC, 1
        """).fetchall()
        revenue_concentration = [
            {"name": s, "value": round(v), "customers": n}
            for s, v, n in seg_rev
        ]

        inactive = con.execute(f"""
            WITH agg AS (
              SELECT c.Customer_ID,
                (SELECT MAX(CAST(s."تاریخ" AS DATE)) FROM sales s
                  WHERE s.Customer_ID = c.Customer_ID) AS last_purchase,
                (SELECT COUNT(*) FROM complaints co
                  WHERE co.Customer_ID = c.Customer_ID) AS complaints
              FROM customers c
            )
            SELECT
              COUNT(*) FILTER (WHERE last_purchase IS NULL) AS never,
              COUNT(*) FILTER (WHERE last_purchase < {ref_lit} - INTERVAL 180 DAY
                               AND last_purchase >= {ref_lit} - INTERVAL 365 DAY) AS d180,
              COUNT(*) FILTER (WHERE last_purchase < {ref_lit} - INTERVAL 365 DAY) AS d365,
              COUNT(*) FILTER (WHERE last_purchase < {ref_lit} - INTERVAL 180 DAY
                               AND complaints > 0) AS inactive_with_complaints
            FROM agg
        """).fetchone()
        churn_factors = {
            "never_bought": inactive[0] or 0,
            "inactive_180_365": inactive[1] or 0,
            "inactive_over_365": inactive[2] or 0,
            "inactive_with_complaints": inactive[3] or 0,
        }

        return {
            "atRisk": at_risk,
            "complaintThemes": complaint_themes,
            "revenueConcentration": revenue_concentration,
            "churnFactors": churn_factors,
            "incomeRecommendations": _income_recommendations(con),
        }
    finally:
        con.close()


def customers() -> list[dict[str, Any]]:
    con = _connect()
    try:
        rows = _rows(con, """
            SELECT c.Customer_ID, c.Customer_Segment, c.Customer_Status,
                   c.Credit_Limit, c.Payment_Terms_Days, c.Relationship_Start_Date,
                   c.Sales_Rep_ID,
                   COALESCE(s.orders, 0)    AS orders,
                   COALESCE(s.revenue, 0)   AS revenue,
                   COALESCE(cm.complaints, 0) AS complaints
            FROM customers c
            LEFT JOIN (
                SELECT Customer_ID,
                       COUNT(DISTINCT "شماره فاکتور") AS orders,
                       SUM("مبلغ کل") AS revenue
                FROM sales GROUP BY 1
            ) s ON c.Customer_ID = s.Customer_ID
            LEFT JOIN (
                SELECT Customer_ID, COUNT(*) AS complaints
                FROM complaints GROUP BY 1
            ) cm ON c.Customer_ID = cm.Customer_ID
            ORDER BY revenue DESC
        """)
        return [
            {
                "Customer_ID": r[0],
                "Customer_Segment": r[1],
                "Customer_Status": r[2],
                "Credit_Limit": r[3],
                "Payment_Terms_Days": r[4],
                "Relationship_Start_Date": r[5],
                "Sales_Rep_ID": r[6],
                "orders": r[7],
                "revenue": r[8],
                "complaints": r[9],
            }
            for r in rows
        ]
    finally:
        con.close()


def _table_columns(con: duckdb.DuckDBPyConnection, table: str) -> list[str]:
    return [d[0] for d in con.execute(f"DESCRIBE {table}").fetchall()]


def _signal_tone(status: str) -> str:
    return {
        "critical": "negative",
        "warning": "neutral",
        "positive": "positive",
        "neutral": "neutral",
        "low": "positive",
        "high": "negative",
        "unknown": "neutral",
    }.get(status, "neutral")


def _signal_detail(sig_id: str, status: str) -> str:
    from backend.crm.labels import STATUS_FA
    return f"وضعیت: {STATUS_FA.get(status, status)}"


def _level_from_status(status: str) -> str:
    return {
        "critical": "زیاد",
        "high": "زیاد",
        "warning": "متوسط",
        "neutral": "متوسط",
        "low": "کم",
        "unknown": "متوسط",
    }.get(status, "متوسط")


def _customer_fingerprint(con: duckdb.DuckDBPyConnection,
                          customer_id: str) -> str:
    """Cheap per-customer data fingerprint: row counts + newest dates of the
    tables that feed the 360 view. The deterministic payload is cached under
    this fingerprint so repeat visits read instantly and the cache invalidates
    automatically when the underlying data changes."""
    from backend.crm import cache as store
    row = con.execute("""
        SELECT
          (SELECT COUNT(*) FROM sales s WHERE s.Customer_ID = ?),
          (SELECT COUNT(*) FROM complaints c WHERE c.Customer_ID = ?),
          (SELECT COUNT(*) FROM crm_interactions i WHERE i.Customer_ID = ?),
          (SELECT COUNT(*) FROM dev_requests d WHERE d.Customer_ID = ?),
          (SELECT COUNT(*) FROM offers o WHERE o.Customer_ID = ?),
          (SELECT COUNT(*) FROM collections col WHERE col.Customer_ID = ?),
          (SELECT COUNT(*) FROM market_signals m WHERE m.Customer_ID = ?),
          (SELECT COALESCE(MAX(s."تاریخ"),'') FROM sales s WHERE s.Customer_ID = ?),
          (SELECT COALESCE(MAX(c.Created_At),'') FROM complaints c WHERE c.Customer_ID = ?),
          (SELECT COALESCE(MAX(i.Event_Time),'') FROM crm_interactions i WHERE i.Customer_ID = ?)
    """, [customer_id] * 10).fetchone()
    return store.fingerprint(row)


def customer_360(customer_id: str) -> dict[str, Any] | None:
    """Full customer-360 payload (all dataset sections + cached LLM summary).
    The deterministic part is cached per customer under a data fingerprint, so
    the first visit computes it and every later visit reads it instantly. The
    LLM summary status is NEVER cached inside the payload: it is overlaid live
    from the summary cache (and re-validated against the current payload
    fingerprint), so a freshly generated summary is visible immediately and a
    stale one is correctly reported as not-ready."""
    from backend.crm import cache as store
    con = _connect()
    try:
        if not con.execute(
                "SELECT 1 FROM customers WHERE Customer_ID = ?",
                [customer_id]).fetchone():
            return None
        fp = _customer_fingerprint(con, customer_id)
    finally:
        con.close()

    payload = store.cached("customer360_data", customer_id,
                           lambda: _customer_360_compute(customer_id), fp)
    if payload is None or not payload.get("customer"):
        return None

    # Live summary overlay (fingerprint-validated against THIS payload).
    from backend.agents import intel_summary
    snapshot = intel_summary._customer_snapshot(payload)
    sum_fp = store.fingerprint(snapshot)
    entry = store.load("customer360", customer_id)
    if entry is not None and entry.get("fingerprint") == sum_fp:
        payload["summary"] = entry["value"]
        payload["summaryReady"] = True
    else:
        payload["summary"] = None
        payload["summaryReady"] = False
    return payload


def _customer_360_compute(customer_id: str) -> dict[str, Any]:
    con = _connect()
    try:
        base = con.execute(
            "SELECT * FROM customers WHERE Customer_ID = ?", [customer_id]
        ).fetchall()
        if not base:
            return {"customer": {}}
        cols = _table_columns(con, "customers")
        cust = dict(zip(cols, base[0]))

        rev_agg = con.execute("""
            SELECT COUNT(DISTINCT "شماره فاکتور"), SUM("مبلغ کل"),
                   MAX("تاریخ")
            FROM sales WHERE Customer_ID = ?
        """, [customer_id]).fetchone()
        orders = rev_agg[0] or 0
        revenue = rev_agg[1] or 0
        last_purchase = rev_agg[2]

        top_prod = con.execute("""
            SELECT Product_ID, SUM("مبلغ کل") AS v
            FROM sales WHERE Customer_ID = ? GROUP BY 1 ORDER BY v DESC LIMIT 1
        """, [customer_id]).fetchone()

        cm_count = con.execute(
            "SELECT COUNT(*) FROM complaints WHERE Customer_ID = ?",
            [customer_id]).fetchone()[0]
        cm_unresolved = con.execute(
            "SELECT COUNT(*) FROM complaints WHERE Customer_ID = ? AND Complaint_Status != 'بسته‌شده'",
            [customer_id]).fetchone()[0]
        cm_reasons = con.execute("""
            SELECT Complaint_Title, COUNT(*) AS v
            FROM complaints WHERE Customer_ID = ?
            GROUP BY 1 ORDER BY v DESC, 1 LIMIT 5
        """, [customer_id]).fetchall()

        coll = con.execute("""
            SELECT COUNT(*), SUM("مبلغ وصول") FROM collections
            WHERE Customer_ID = ?
        """, [customer_id]).fetchone()
        coll_count = coll[0] or 0
        coll_amount = coll[1] or 0

        avg_order_value = round(revenue / orders) if orders else 0

        # ---- deterministic engine: signals / state / reasons / actions ----
        from backend.crm.labels import (
            SIGNAL_FA, action_name, action_next_step, status_fa,
            translate_reason, translate_reasons,
        )
        from backend.crm.service import service
        ci = service.get_intelligence(customer_id)
        engine_signals = [
            {
                "id": sig_id,
                "label": SIGNAL_FA.get(sig_id, sig_id),
                "tone": _signal_tone(s.status),
                "detail": _signal_detail(sig_id, s.status),
                "reasons": translate_reasons(s.reasons[:2]),
            }
            for sig_id, s in ci.signals.items()
            if s is not None
        ]
        risk_level = _level_from_status(
            ci.state.churn_risk.status if ci.state else "unknown")
        actions = [
            {
                "id": a.action_id,
                "name": action_name(a.action_id, a.name),
                "reason": translate_reason(a.reason),
                "evidence": translate_reasons(a.evidence[:2]),
                "next_step": action_next_step(a.action_id, a.suggested_next_step),
            }
            for a in ci.next_best_actions[:6]
        ]
        state_dims = {}
        if ci.state:
            for dim in ("value", "churn_risk", "growth_opportunity",
                        "relationship_health", "profitability", "payment_risk"):
                d = getattr(ci.state, dim)
                state_dims[dim] = {
                    "status": status_fa(d.status),
                    "reasons": translate_reasons(d.reasons[:2]),
                }

        # ---- list sections (minimal previews served; UI expands) ----
        complaints_rows = con.execute("""
            SELECT Complaint_ID, Created_At, Complaint_Title, Complaint_Text,
                   Severity, Complaint_Status, Product_ID
            FROM complaints WHERE Customer_ID = ? AND Complaint_ID IS NOT NULL
            ORDER BY Created_At DESC LIMIT 100
        """, [customer_id]).fetchall()
        complaints = [
            {
                "id": r[0],
                "date": r[1],
                "title": r[2],
                "text": r[3],
                "severity": r[4],
                "status": r[5],
                "product": r[6],
            }
            for r in complaints_rows
        ]

        interactions_rows = con.execute("""
            SELECT Interaction_ID, Event_Time, Interaction_Type, Summary_Text,
                   Next_Action, Sales_Rep_ID
            FROM crm_interactions WHERE Customer_ID = ?
            ORDER BY Event_Time DESC LIMIT 100
        """, [customer_id]).fetchall()
        interactions = [
            {
                "id": r[0],
                "date": r[1],
                "type": r[2],
                "summary": r[3],
                "next_action": r[4],
                "rep": r[5],
            }
            for r in interactions_rows
        ]

        tx_rows = con.execute("""
            SELECT "شماره فاکتور", MAX("تاریخ") AS d, SUM("مبلغ کل") AS v,
                   COUNT(*) AS lines
            FROM sales WHERE Customer_ID = ?
            GROUP BY 1 ORDER BY d DESC LIMIT 50
        """, [customer_id]).fetchall()
        transactions = [
            {
                "invoice": r[0],
                "date": r[1],
                "amount": r[2] or 0,
                "lines": r[3],
            }
            for r in tx_rows
        ]

        dev_rows = con.execute("""
            SELECT Request_ID, Created_At, Request_Type, Requirement_Text,
                   Status, Owner_Unit
            FROM dev_requests WHERE Customer_ID = ?
            ORDER BY Created_At DESC LIMIT 100
        """, [customer_id]).fetchall()
        dev_requests = [
            {
                "id": r[0],
                "date": r[1],
                "type": r[2],
                "text": r[3],
                "status": r[4],
                "owner": r[5],
            }
            for r in dev_rows
        ]
        dev_open = sum(1 for d in dev_requests if d["status"] not in ("بسته‌شده", "انجام‌شده"))

        offer_rows = con.execute("""
            SELECT Offer_ID, Offer_Date, Offer_Type, Offer_Discount_Pct,
                   Result, Product_ID
            FROM offers WHERE Customer_ID = ?
            ORDER BY Offer_Date DESC LIMIT 100
        """, [customer_id]).fetchall()
        offers = [
            {
                "id": r[0],
                "date": r[1],
                "type": r[2],
                "discount_pct": r[3],
                "result": r[4],
                "product": r[5],
            }
            for r in offer_rows
        ]
        offer_accepted = sum(1 for o in offers if o["result"] == "قبول")
        offer_acceptance = (offer_accepted / len(offers)) if offers else None
        best_offer = con.execute("""
            SELECT Offer_Type, COUNT(*) AS n,
                   SUM(CASE WHEN Result = 'قبول' THEN 1 ELSE 0 END) AS accepted
            FROM offers WHERE Customer_ID = ?
            GROUP BY 1 ORDER BY accepted * 1.0 / COUNT(*) DESC LIMIT 1
        """, [customer_id]).fetchone()
        best_offer_type = best_offer[0] if best_offer else None

        coll_rows = con.execute("""
            SELECT Collection_ID, "تاریخ رویداد وصول", "مبلغ وصول", "روز تأخیر",
                   "چک برگشتی"
            FROM collections WHERE Customer_ID = ?
            ORDER BY "تاریخ رویداد وصول" DESC LIMIT 50
        """, [customer_id]).fetchall()
        collections = [
            {
                "id": r[0],
                "date": r[1],
                "amount": r[2] or 0,
                "delay_days": r[3],
                "bounced": r[4],
            }
            for r in coll_rows
        ]

        market_rows = con.execute("""
            SELECT Report_Date, Product_Market, Competitor, Customer_Signal,
                   Demand_Change, Market_Trend
            FROM market_signals WHERE Customer_ID = ?
            ORDER BY Report_Date DESC LIMIT 50
        """, [customer_id]).fetchall()
        market_signals = [
            {
                "date": r[0],
                "market": r[1],
                "competitor": r[2],
                "customer_signal": r[3],
                "demand": r[4],
                "trend": r[5],
            }
            for r in market_rows
        ]

        interactions_count = con.execute(
            "SELECT COUNT(*) FROM crm_interactions WHERE Customer_ID = ?",
            [customer_id]).fetchone()[0] or 0
        dev_count = len(dev_requests)

        overdue_amount = con.execute("""
            SELECT COALESCE(SUM("مبلغ وصول"), 0) FROM collections
            WHERE Customer_ID = ? AND "روز تأخیر" > 0
        """, [customer_id]).fetchone()[0] or 0
        bounced_checks = con.execute("""
            SELECT COUNT(*) FROM collections
            WHERE Customer_ID = ? AND "چک برگشتی" = 'بله'
        """, [customer_id]).fetchone()[0] or 0

        # Summary state is overlaid live by customer_360(), never cached here.
        summary = None
        summary_ready = False

        # Curated, human-readable profile — raw internal ids/system fields are
        # deliberately excluded (they are not meaningful to a sales manager).
        customer_profile = [
            {"label": "بخش بازار", "value": cust.get("Customer_Segment")},
            {"label": "وضعیت", "value": cust.get("Customer_Status")},
            {"label": "شروع همکاری", "value": cust.get("Relationship_Start_Date")},
            {"label": "سقف اعتبار", "value": cust.get("Credit_Limit")},
            {"label": "شرایط پرداخت", "value": cust.get("Payment_Terms_Days")},
        ]

        return {
            "customer": cust,
            "customerProfile": customer_profile,
            "summary": summary,
            "summaryReady": summary_ready,
            "riskScore": ci.state.churn_risk.score if ci.state else None,
            "riskLevel": risk_level,
            "riskSignals": engine_signals,
            "state": state_dims,
            "actions": actions,
            "orders": orders,
            "revenue": revenue,
            "avgOrderValue": avg_order_value,
            "lastPurchase": last_purchase,
            "topProduct": top_prod[0] if top_prod else None,
            "complaints": cm_count,
            "unresolvedComplaints": cm_unresolved,
            "complaintReasons": [
                {"reason": r, "count": c} for r, c in cm_reasons
            ],
            "complaintList": complaints,
            "interactions": interactions,
            "interactionsCount": interactions_count,
            "transactions": transactions,
            "devRequests": dev_requests,
            "devCount": dev_count,
            "devOpen": dev_open,
            "offers": offers,
            "offerAcceptance": offer_acceptance,
            "bestOfferType": best_offer_type,
            "collections": collections,
            "collectionsCount": coll_count,
            "collectionsAmount": coll_amount,
            "overdueAmount": overdue_amount,
            "bouncedChecks": bounced_checks,
            "marketSignals": market_signals,
        }
    finally:
        con.close()


def date_ref() -> "datetime.date":
    """Reference date for recency: the max sale date across the dataset."""
    import datetime as _dt
    con = _connect()
    try:
        mx = con.execute('SELECT MAX("تاریخ") FROM sales').fetchone()[0]
        return _dt.date.fromisoformat(mx[:10]) if mx else _dt.date.today()
    except Exception:  # noqa: BLE001
        return _dt.date.today()
    finally:
        con.close()
