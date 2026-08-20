"""Signal 1 — Real Profit.

revenue - product_cost - discounts - return_cost. Discount data is not stored
on sales lines in this schema, so it is reported as "not available" (0) rather
than silently invented. When cost records are missing the signal degrades to
``unknown`` instead of substituting revenue for profit.
"""
from __future__ import annotations

import datetime as dt

import duckdb

from backend.crm.config import ProfitConfig, SignalConfig
from backend.crm.data import safefloat
from backend.crm.schemas import CustomerSignal
from backend.crm.signals.base import signal


_PROFIT_SQL = """
SELECT
    COALESCE(SUM(s."مبلغ کل"), 0)                       AS revenue,
    COUNT(DISTINCT s."شماره فاکتور")                     AS orders,
    COUNT(*)                                             AS lines,
    COALESCE(SUM(c."هزینه کل به ازای واحد" * s."مقدار"), 0) AS product_cost,
    COALESCE(SUM(c."مبلغ برگشتی"), 0)                    AS return_amount,
    COUNT(c.Cost_Record_ID)                              AS costed_lines,
    COALESCE(SUM(CASE WHEN c.Cost_Record_ID IS NOT NULL
                      THEN s."مبلغ کل" ELSE 0 END), 0)    AS costed_revenue
FROM sales s
LEFT JOIN realized_costs c ON s.Sales_Line_ID = c.Sales_Line_ID
WHERE s.Customer_ID = ?
"""


def _classify(margin: float, cfg: ProfitConfig) -> str:
    if margin >= cfg.high_profit_margin:
        return "high_profit"
    if margin >= cfg.normal_profit_margin:
        return "normal_profit"
    if margin >= cfg.low_profit_margin:
        return "low_profit"
    return "negative_profit"


_STATUS_MAP = {
    "high_profit": "positive",
    "normal_profit": "neutral",
    "low_profit": "warning",
    "negative_profit": "critical",
}


def calculate(con: duckdb.DuckDBPyConnection, customer_id: str,
              ref: dt.date, cfg: SignalConfig) -> CustomerSignal:
    row = con.execute(_PROFIT_SQL, [customer_id]).fetchone()
    revenue = safefloat(row[0]) or 0.0
    orders = int(row[1] or 0)
    product_cost = safefloat(row[3]) or 0.0
    return_amount = safefloat(row[4]) or 0.0
    costed_revenue = safefloat(row[6]) or 0.0

    if revenue <= 0 or orders == 0:
        return signal("profit", customer_id, status="unknown", confidence=0.0,
                      sample_size=0,
                      evidence={"revenue": revenue, "orders": orders},
                      reasons=["No sales revenue available"])

    coverage = (costed_revenue / revenue) if revenue else 0.0

    # No cost data at all -> cannot compute profit; do NOT substitute revenue.
    if costed_revenue <= 0:
        return signal("profit", customer_id, status="unknown", confidence=0.0,
                      sample_size=orders,
                      evidence={"revenue": round(revenue, 2), "orders": orders,
                                "cost_coverage": 0.0},
                      reasons=["Required cost data is unavailable"])

    profit = revenue - product_cost - return_amount
    margin = profit / revenue

    classification = _classify(margin, cfg.profit)

    # Partial cost coverage -> margin is unreliable; report it but flag it.
    if coverage < cfg.profit.min_cost_coverage:
        return signal(
            "profit", customer_id,
            value=round(profit, 2),
            score=round(margin * 100, 2),
            status="low_confidence",
            direction="neutral",
            confidence=round(max(0.0, coverage), 3),
            sample_size=orders,
            evidence={
                "total_revenue": round(revenue, 2),
                "total_cost": round(product_cost, 2),
                "total_discount": 0.0,
                "discount_available": False,
                "return_amount": round(return_amount, 2),
                "real_profit": round(profit, 2),
                "profit_margin": round(margin, 4),
                "cost_coverage": round(coverage, 3),
                "classification": classification,
                "orders": orders,
            },
            reasons=[f"Profit margin is {margin:.1%} but cost data covers only "
                     f"{coverage:.0%} of revenue, so it is not reliable"],
        )

    confidence = min(1.0, coverage)

    return signal(
        "profit", customer_id,
        value=round(profit, 2),
        score=round(margin * 100, 2),
        status=_STATUS_MAP[classification],
        direction="neutral",
        confidence=round(confidence, 3),
        sample_size=orders,
        evidence={
            "total_revenue": round(revenue, 2),
            "total_cost": round(product_cost, 2),
            "total_discount": 0.0,
            "discount_available": False,
            "return_amount": round(return_amount, 2),
            "real_profit": round(profit, 2),
            "profit_margin": round(margin, 4),
            "cost_coverage": round(coverage, 3),
            "classification": classification,
            "orders": orders,
        },
        reasons=[f"Profit margin is {margin:.1%} "
                 f"(cost coverage {coverage:.0%})"],
    )
