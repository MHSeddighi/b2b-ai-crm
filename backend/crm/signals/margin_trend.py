"""Signal 6 — Margin Trend.

Customer margin over the current window vs the previous comparable window,
computed on cost-matched sales lines only (margin needs revenue AND cost).
"""
from __future__ import annotations

import datetime as dt

import duckdb

from backend.crm.config import MarginTrendConfig, SignalConfig
from backend.crm.data import safefloat, window_bounds
from backend.crm.schemas import CustomerSignal
from backend.crm.signals.base import signal


_MARGIN_SQL = """
SELECT
    COALESCE(SUM(CASE WHEN s."تاریخ" BETWEEN ? AND ? AND c.Cost_Record_ID IS NOT NULL
                      THEN s."مبلغ کل" END), 0) AS cur_rev,
    COALESCE(SUM(CASE WHEN s."تاریخ" BETWEEN ? AND ? AND c.Cost_Record_ID IS NOT NULL
                      THEN c."هزینه کل به ازای واحد" * s."مقدار" END), 0) AS cur_cost,
    COALESCE(SUM(CASE WHEN s."تاریخ" BETWEEN ? AND ? AND c.Cost_Record_ID IS NOT NULL
                      THEN s."مبلغ کل" END), 0) AS prev_rev,
    COALESCE(SUM(CASE WHEN s."تاریخ" BETWEEN ? AND ? AND c.Cost_Record_ID IS NOT NULL
                      THEN c."هزینه کل به ازای واحد" * s."مقدار" END), 0) AS prev_cost
FROM sales s
LEFT JOIN realized_costs c ON s.Sales_Line_ID = c.Sales_Line_ID
WHERE s.Customer_ID = ?
"""


def _classify(change: float | None, cfg: MarginTrendConfig) -> str:
    if change is None:
        return "unknown"
    if change >= cfg.improving:
        return "improving"
    if change <= cfg.strong_decline:
        return "strong_decline"
    if change <= cfg.declining:
        return "declining"
    return "stable"


_DIRECTION = {"improving": "improving", "stable": "stable",
              "declining": "declining", "strong_decline": "declining",
              "unknown": "unknown"}
_STATUS = {"improving": "positive", "stable": "neutral",
           "declining": "warning", "strong_decline": "critical",
           "unknown": "unknown"}


def _margin(rev: float, cost: float) -> float | None:
    if rev <= 0:
        return None
    return (rev - cost) / rev


def calculate(con: duckdb.DuckDBPyConnection, customer_id: str,
              ref: dt.date, cfg: SignalConfig) -> CustomerSignal:
    rs, re = window_bounds(ref, cfg.time.margin_period_months * 30)
    ps, pe = window_bounds(ref - dt.timedelta(days=cfg.time.margin_period_months * 30),
                           cfg.time.margin_period_months * 30)
    row = con.execute(_MARGIN_SQL, [rs, re, rs, re, ps, pe, ps, pe,
                                    customer_id]).fetchone()

    cur_rev = safefloat(row[0]) or 0.0
    cur_cost = safefloat(row[1]) or 0.0
    prev_rev = safefloat(row[2]) or 0.0
    prev_cost = safefloat(row[3]) or 0.0

    cur_margin = _margin(cur_rev, cur_cost)
    prev_margin = _margin(prev_rev, prev_cost)

    if cur_margin is None or prev_margin is None:
        return signal("margin_trend", customer_id, status="unknown",
                      confidence=0.0, sample_size=0,
                      value=cur_margin,
                      reasons=["Insufficient cost-matched sales to compute margin trend"])

    change = cur_margin - prev_margin
    classification = _classify(change, cfg.margin_trend)

    return signal(
        "margin_trend", customer_id,
        value=round(change, 4),
        score=round((cur_margin or 0.0) * 100, 2),
        status=_STATUS[classification],
        direction=_DIRECTION[classification],
        confidence=0.8,
        sample_size=0,
        evidence={
            "classification": classification,
            "current_margin": round(cur_margin, 4),
            "previous_margin": round(prev_margin, 4),
            "margin_change": round(change, 4),
        },
        reasons=[f"Margin moved from {prev_margin:.1%} to {cur_margin:.1%} "
                 f"(change {change:+.1%})"],
    )
