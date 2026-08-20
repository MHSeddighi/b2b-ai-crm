"""Signal 2 — Purchase Trend.

Recent rolling window vs the immediately preceding comparable window, so a
trend is relative to the customer's own baseline — never an absolute number.
Avoids declaring a trend when there is no comparable history.
"""
from __future__ import annotations

import datetime as dt

import duckdb

from backend.crm.config import PurchaseTrendConfig, SignalConfig
from backend.crm.data import pct_change, safefloat, window_bounds
from backend.crm.schemas import CustomerSignal
from backend.crm.signals.base import signal


_TREND_SQL = """
SELECT
    COALESCE(SUM(CASE WHEN "تاریخ" BETWEEN ? AND ? THEN "مبلغ کل" END), 0)  AS recent_rev,
    COALESCE(SUM(CASE WHEN "تاریخ" BETWEEN ? AND ? THEN "مبلغ کل" END), 0)  AS prev_rev,
    COUNT(DISTINCT CASE WHEN "تاریخ" BETWEEN ? AND ? THEN "شماره فاکتور" END) AS recent_orders,
    COUNT(DISTINCT CASE WHEN "تاریخ" BETWEEN ? AND ? THEN "شماره فاکتور" END) AS prev_orders,
    COALESCE(SUM(CASE WHEN "تاریخ" BETWEEN ? AND ? THEN "مقدار" END), 0)    AS recent_qty,
    COALESCE(SUM(CASE WHEN "تاریخ" BETWEEN ? AND ? THEN "مقدار" END), 0)    AS prev_qty
FROM sales
WHERE Customer_ID = ?
"""


def _classify(change: float | None, cfg: PurchaseTrendConfig) -> str:
    if change is None:
        return "insufficient_data"
    if change >= cfg.strong_growth:
        return "strong_growth"
    if change >= cfg.growth:
        return "growth"
    if change <= cfg.strong_decline:
        return "strong_decline"
    if change <= cfg.decline:
        return "decline"
    return "stable"


_DIRECTION = {
    "strong_growth": "improving", "growth": "improving",
    "stable": "stable",
    "decline": "declining", "strong_decline": "declining",
    "insufficient_data": "unknown",
}
_STATUS = {
    "strong_growth": "positive", "growth": "positive",
    "stable": "neutral",
    "decline": "warning", "strong_decline": "critical",
    "insufficient_data": "unknown",
}


def calculate(con: duckdb.DuckDBPyConnection, customer_id: str,
              ref: dt.date, cfg: SignalConfig) -> CustomerSignal:
    rs, re = window_bounds(ref, cfg.time.recent_window_days)
    ps, pe = window_bounds(ref - dt.timedelta(days=cfg.time.recent_window_days),
                           cfg.time.previous_window_days)
    row = con.execute(_TREND_SQL, [rs, re, ps, pe, rs, re, ps, pe,
                                   rs, re, ps, pe, customer_id]).fetchone()

    recent_rev = safefloat(row[0]) or 0.0
    prev_rev = safefloat(row[1]) or 0.0
    recent_orders = int(row[2] or 0)
    prev_orders = int(row[3] or 0)
    recent_qty = safefloat(row[4]) or 0.0
    prev_qty = safefloat(row[5]) or 0.0

    total_orders = recent_orders + prev_orders
    rev_change = pct_change(recent_rev, prev_rev)
    order_change = pct_change(float(recent_orders), float(prev_orders))
    qty_change = pct_change(recent_qty, prev_qty)

    # No comparable baseline -> cannot honestly call a trend.
    if prev_rev <= 0 and prev_orders == 0:
        return signal(
            "purchase_trend", customer_id, status="unknown", direction="unknown",
            confidence=0.0, sample_size=total_orders,
            value=rev_change,
            evidence={"recent_revenue": recent_rev, "previous_revenue": prev_rev,
                      "recent_orders": recent_orders, "previous_orders": prev_orders},
            reasons=["Insufficient history: no comparable previous period"],
        )

    if total_orders < cfg.time.min_orders_for_trend:
        return signal(
            "purchase_trend", customer_id, status="unknown", direction="unknown",
            confidence=0.0, sample_size=total_orders, value=rev_change,
            evidence={"recent_orders": recent_orders, "previous_orders": prev_orders},
            reasons=["Insufficient order history to establish a trend"],
        )

    classification = _classify(rev_change, cfg.purchase_trend)
    # More history -> more confidence in the trend (capped at 1).
    confidence = min(1.0, total_orders / 10.0)

    return signal(
        "purchase_trend", customer_id,
        value=round(rev_change, 4) if rev_change is not None else None,
        score=round((rev_change or 0.0) * 100, 2),
        status=_STATUS[classification],
        direction=_DIRECTION[classification],
        confidence=round(confidence, 3),
        sample_size=total_orders,
        evidence={
            "classification": classification,
            "current_period_value": round(recent_rev, 2),
            "previous_period_value": round(prev_rev, 2),
            "revenue_change_pct": round(rev_change * 100, 2) if rev_change is not None else None,
            "order_change_pct": round(order_change * 100, 2) if order_change is not None else None,
            "quantity_change_pct": round(qty_change * 100, 2) if qty_change is not None else None,
            "recent_orders": recent_orders,
            "previous_orders": prev_orders,
        },
        reasons=[f"Revenue changed {rev_change:.0%} "
                 f"({recent_orders} vs {prev_orders} orders)"] if rev_change is not None
        else ["Insufficient data to establish a trend"],
    )
