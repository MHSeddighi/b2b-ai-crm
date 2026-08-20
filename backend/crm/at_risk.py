"""Engine-based at-risk customer ranking (real churn signals, cached).

Ranking customers by risk must use the deterministic signal engine, not a
hand-written SQL heuristic: for every customer we run the base signals the
churn-risk signal actually consumes (purchase trend, purchase cycle, complaint
impact, payment behaviour, share of wallet), derive the real churn-risk score,
and sort by it. The result is cached under the global data fingerprint — one
full computation, instant reads afterwards (the dataset is static in practice).
"""
from __future__ import annotations

from typing import Any

from backend.crm import cache as store
from backend.crm import data
from backend.crm.config import SIGNAL_CONFIG
from backend.crm.signals import (
    churn_risk,
    complaint_impact,
    payment_behavior,
    purchase_cycle,
    purchase_trend,
    share_of_wallet,
)

# The base signals the churn-risk signal actually consumes (see churn_risk.py).
_CHURN_BASE = {
    "purchase_trend": purchase_trend.calculate,
    "payment_behavior": payment_behavior.calculate,
    "share_of_wallet": share_of_wallet.calculate,
    "purchase_cycle": purchase_cycle.calculate,
    "complaint_impact": complaint_impact.calculate,
}

_LEVEL = {
    "critical": "زیاد",
    "high": "زیاد",
    "warning": "متوسط",
    "low": "کم",
    "neutral": "کم",
    "unknown": "متوسط",
}


def _churn_signal(con, customer_id, ref, cfg):
    signals = {}
    for signal_id, fn in _CHURN_BASE.items():
        signals[signal_id] = fn(con, customer_id, ref, cfg)
    return churn_risk.calculate(customer_id, signals, ref, cfg)


def _compute(limit: int) -> list[dict[str, Any]]:
    con = data.connect()
    try:
        ref = data.reference_date(con)
        cfg = SIGNAL_CONFIG
        agg_rows = con.execute("""
            SELECT c.Customer_ID, c.Customer_Segment, c.Customer_Status,
              (SELECT COUNT(*) FROM complaints co
                WHERE co.Customer_ID = c.Customer_ID) AS complaints,
              (SELECT COUNT(DISTINCT s."شماره فاکتور") FROM sales s
                WHERE s.Customer_ID = c.Customer_ID) AS orders,
              (SELECT COALESCE(SUM(s."مبلغ کل"), 0) FROM sales s
                WHERE s.Customer_ID = c.Customer_ID) AS revenue,
              (SELECT MAX(CAST(s."تاریخ" AS DATE)) FROM sales s
                WHERE s.Customer_ID = c.Customer_ID) AS last_purchase,
              (SELECT COUNT(*) FROM collections col
                WHERE col.Customer_ID = c.Customer_ID
                  AND col."چک برگشتی" = 'بله') AS bounced
            FROM customers c
        """).fetchall()
        agg = {r[0]: r for r in agg_rows}

        out: list[dict[str, Any]] = []
        for cid, r in agg.items():
            try:
                churn = _churn_signal(con, cid, ref, cfg)
            except Exception:  # noqa: BLE001 — a broken customer must not abort the pass
                continue
            if churn is None or churn.score is None:
                continue
            last = r[6]
            days = (ref - last).days if last else None
            out.append({
                "customer_id": cid,
                "segment": r[1],
                "status": r[2],
                "complaints": r[3],
                "orders": r[4],
                "revenue": r[5],
                "last_purchase": last.isoformat() if last else None,
                "days_since": days,
                "bounced": r[7],
                "risk_score": round(churn.score, 2),
                "risk_level": _LEVEL.get(churn.status, "متوسط"),
            })
        # Highest churn risk first; revenue breaks ties (protect the big accounts)
        out.sort(key=lambda x: (-x["risk_score"], -x["revenue"], x["customer_id"]))
        return out[:limit]
    finally:
        con.close()


def engine_at_risk(limit: int = 50) -> list[dict[str, Any]]:
    """Top at-risk customers ranked by the engine's real churn-risk score.

    Cached under the global data fingerprint: the first call runs the full
    per-customer signal pass, later calls read the cached ranking instantly.
    """
    con = data.connect()
    try:
        fp = data.global_fingerprint(con)
    finally:
        con.close()
    full = store.cached("at_risk_engine", "overview",
                        lambda: _compute(max(limit, 50)), fp)
    return full[:limit]
