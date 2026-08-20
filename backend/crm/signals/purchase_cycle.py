"""Signal 5 — Purchase Cycle Deviation.

Compares days-since-last-purchase against the customer's own historical median
inter-purchase interval (robust median, not a fragile average). Skipped for
customers with too little history.
"""
from __future__ import annotations

import datetime as dt
import statistics

import duckdb

from backend.crm.config import PurchaseCycleConfig, SignalConfig
from backend.crm.data import as_date
from backend.crm.schemas import CustomerSignal
from backend.crm.signals.base import signal


_CYCLE_SQL = """
SELECT DISTINCT "تاریخ"
FROM sales
WHERE Customer_ID = ?
ORDER BY "تاریخ" ASC
"""


def calculate(con: duckdb.DuckDBPyConnection, customer_id: str,
              ref: dt.date, cfg: SignalConfig) -> CustomerSignal:
    dates = [as_date(r[0]) for r in con.execute(_CYCLE_SQL, [customer_id]).fetchall()]

    if len(dates) < cfg.time.min_orders_for_cycle:
        return signal("purchase_cycle", customer_id, status="unknown",
                      confidence=0.0, sample_size=len(dates),
                      reasons=["Insufficient purchase history for cycle analysis"])

    gaps = sorted((dates[i + 1] - dates[i]).days for i in range(len(dates) - 1))
    # guard: gaps are strictly positive by DISTINCT ordering
    gaps = [g for g in gaps if g > 0]
    if not gaps:
        return signal("purchase_cycle", customer_id, status="unknown",
                      confidence=0.0, sample_size=len(dates),
                      reasons=["Insufficient distinct purchase dates"])

    median_gap = statistics.median(gaps)
    days_since = (ref - dates[-1]).days
    ratio = days_since / median_gap if median_gap else None

    if ratio is None:
        return signal("purchase_cycle", customer_id, status="unknown",
                      confidence=0.0, sample_size=len(dates),
                      reasons=["Cannot compute cycle deviation"])

    cfg_c = cfg.purchase_cycle
    if ratio >= cfg_c.critical_ratio:
        classification, status = "severely_late", "critical"
    elif ratio >= cfg_c.warning_ratio:
        classification, status = "significantly_late", "warning"
    elif ratio >= 1.0:
        classification, status = "slightly_late", "neutral"
    else:
        classification, status = "normal", "positive"

    confidence = min(1.0, (len(gaps)) / 8.0)

    return signal(
        "purchase_cycle", customer_id,
        value=round(ratio, 3),
        score=round(min(100.0, max(0.0, (ratio - 0.5) * 50.0)), 2),
        status=status,
        direction="declining" if ratio >= cfg_c.warning_ratio else "stable",
        confidence=round(confidence, 3),
        sample_size=len(dates),
        evidence={
            "classification": classification,
            "normal_cycle_days": round(median_gap, 1),
            "days_since_last_purchase": days_since,
            "cycle_deviation_ratio": round(ratio, 3),
            "distinct_purchases": len(dates),
        },
        reasons=[f"Customer is {days_since} days since last purchase vs a "
                 f"normal cycle of {median_gap:.0f} days (ratio {ratio:.2f})"],
    )
