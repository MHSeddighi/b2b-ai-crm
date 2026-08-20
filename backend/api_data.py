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


def customer_360(customer_id: str) -> dict[str, Any] | None:
    con = _connect()
    try:
        base = con.execute(
            "SELECT * FROM customers WHERE Customer_ID = ?", [customer_id]
        ).fetchall()
        if not base:
            return None
        cols = [d[0] for d in con.execute("DESCRIBE customers").fetchall()]
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
        cm_reasons = con.execute("""
            SELECT Complaint_Title, COUNT(*) AS v
            FROM complaints WHERE Customer_ID = ?
            GROUP BY 1 ORDER BY v DESC LIMIT 5
        """, [customer_id]).fetchall()

        coll = con.execute("""
            SELECT COUNT(*), SUM("مبلغ وصول") FROM collections
            WHERE Customer_ID = ?
        """, [customer_id]).fetchone()
        coll_count = coll[0] or 0
        coll_amount = coll[1] or 0

        avg_order_value = round(revenue / orders) if orders else 0

        # --- deterministic risk model (computed from real data) ---
        risk_signals: list[dict[str, Any]] = []
        if cm_count >= 5:
            risk_signals.append({
                "label": "حجم شکایت", "tone": "negative",
                "detail": f"{cm_count} شکایت ثبت شده"})
        elif cm_count >= 3:
            risk_signals.append({
                "label": "شکایت", "tone": "neutral",
                "detail": f"{cm_count} شکایت ثبت شده"})
        else:
            risk_signals.append({
                "label": "شکایت کم", "tone": "positive",
                "detail": f"فقط {cm_count} شکایت"})

        import datetime as _dt
        days_since = None
        if last_purchase:
            try:
                days_since = (date_ref() - _dt.date.fromisoformat(last_purchase[:10])).days
            except Exception:  # noqa: BLE001
                days_since = None
        if days_since is not None and days_since > 365:
            risk_signals.append({
                "label": "فاصله خرید", "tone": "negative",
                "detail": f"آخرین خرید {days_since} روز پیش"})
        elif days_since is not None and days_since > 180:
            risk_signals.append({
                "label": "فاصله خرید", "tone": "neutral",
                "detail": f"آخرین خرید {days_since} روز پیش"})
        elif days_since is not None:
            risk_signals.append({
                "label": "فاصله خرید", "tone": "positive",
                "detail": f"آخرین خرید {days_since} روز پیش"})

        if orders >= 50:
            risk_signals.append({
                "label": "حجم سفارش", "tone": "positive",
                "detail": f"{orders} سفارش ثبت شده"})
        elif orders == 0:
            risk_signals.append({
                "label": "بدون سفارش", "tone": "negative",
                "detail": "هنوز سفارشی ثبت نشده است"})

        # risk score 0-100
        score = 12
        score += min(45, cm_count * 8)
        if days_since is not None:
            if days_since > 365:
                score += 20
            elif days_since > 180:
                score += 10
        if orders == 0:
            score += 25
        risk_score = min(99, score)

        risk_level = "کم" if risk_score < 35 else ("متوسط" if risk_score < 65 else "زیاد")

        # Persian summary built from real numbers
        parts = [f"مشتری {customer_id}"]
        if revenue:
            parts.append(f"با درآمد کل {revenue:,.0f}")
        if orders:
            parts.append(f"و {orders} سفارش")
        parts.append("در پایگاه‌داده است.")
        summary = " ".join(parts)
        if cm_count:
            summary += (f" {cm_count} شکایت ثبت شده و"
                        f" ریسک فعلی {risk_level} ارزیابی می‌شود.")
        else:
            summary += f" بدون شکایت و ریسک فعلی {risk_level}."

        return {
            "customer": cust,
            "summary": summary,
            "riskScore": risk_score,
            "riskLevel": risk_level,
            "riskSignals": risk_signals,
            "orders": orders,
            "revenue": revenue,
            "avgOrderValue": avg_order_value,
            "lastPurchase": last_purchase,
            "topProduct": top_prod[0] if top_prod else None,
            "complaints": cm_count,
            "complaintReasons": [
                {"reason": r, "count": c} for r, c in cm_reasons
            ],
            "collectionsCount": coll_count,
            "collectionsAmount": coll_amount,
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
