"""Signal 3 — Payment Behaviour.

Delay statistics, overdue ratio, bounced cheques, and abnormal deterioration
of the customer's own historical payment pattern (not a global rule).
"""
from __future__ import annotations

import datetime as dt

import duckdb

from backend.crm.config import PaymentConfig, SignalConfig
from backend.crm.data import safefloat, window_bounds
from backend.crm.schemas import CustomerSignal
from backend.crm.signals.base import signal


_PAY_SQL = """
SELECT
    COALESCE(AVG("روز تأخیر"), 0)   AS avg_delay,
    COALESCE(MEDIAN("روز تأخیر"), 0) AS median_delay,
    COALESCE(MAX("روز تأخیر"), 0)   AS max_delay,
    COUNT(*)                         AS total,
    SUM(CASE WHEN "روز تأخیر" > ? THEN 1 ELSE 0 END) AS late_count,
    SUM(CASE WHEN "چک برگشتی" = 'بله' THEN 1 ELSE 0 END) AS bounced,
    COALESCE(SUM(CASE WHEN "روز تأخیر" > 0 THEN "مبلغ وصول" ELSE 0 END), 0) AS overdue_amount,
    AVG(CASE WHEN "تاریخ رویداد وصول" BETWEEN ? AND ? THEN "روز تأخیر" END) AS recent_avg,
    AVG(CASE WHEN "تاریخ رویداد وصول" BETWEEN ? AND ? THEN "روز تأخیر" END) AS baseline_avg
FROM collections
WHERE Customer_ID = ?
"""


def _classify(median_delay: float, cfg: PaymentConfig) -> str:
    if median_delay <= cfg.excellent_delay:
        return "excellent"
    if median_delay <= cfg.good_delay:
        return "good"
    if median_delay <= cfg.warning_delay:
        return "warning"
    if median_delay <= cfg.poor_delay:
        return "poor"
    return "critical"


_STATUS = {"excellent": "positive", "good": "positive",
           "warning": "warning", "poor": "warning", "critical": "critical"}


def calculate(con: duckdb.DuckDBPyConnection, customer_id: str,
              ref: dt.date, cfg: SignalConfig) -> CustomerSignal:
    rs, re = window_bounds(ref, cfg.time.payment_recent_days)
    ps, pe = window_bounds(
        ref - dt.timedelta(days=cfg.time.payment_recent_days),
        cfg.time.payment_baseline_days,
    )
    row = con.execute(
        _PAY_SQL,
        [cfg.payment.late_threshold_days, rs, re, ps, pe, customer_id],
    ).fetchone()

    avg_delay = safefloat(row[0]) or 0.0
    median_delay = safefloat(row[1]) or 0.0
    max_delay = safefloat(row[2]) or 0.0
    total = int(row[3] or 0)
    late_count = int(row[4] or 0)
    bounced = int(row[5] or 0)
    overdue_amount = safefloat(row[6]) or 0.0
    recent_avg = safefloat(row[7])
    baseline_avg = safefloat(row[8])

    if total == 0:
        return signal("payment_behavior", customer_id, status="unknown",
                      confidence=0.0, sample_size=0,
                      reasons=["No collection / payment records available"])

    classification = _classify(median_delay, cfg.payment)
    overdue_ratio = late_count / total if total else 0.0

    # Deterioration vs the customer's own history.
    deterioration = None
    if recent_avg is not None and baseline_avg is not None and baseline_avg >= 0:
        deterioration = recent_avg - baseline_avg

    direction = "stable"
    if deterioration is not None:
        if deterioration >= cfg.payment.deterioration_days:
            direction = "declining"
        elif deterioration <= -cfg.payment.deterioration_days:
            direction = "improving"

    # Escalate status if there is a marked deterioration even from a good base.
    if direction == "declining" and classification in ("excellent", "good"):
        classification = "warning" if classification == "good" else "good"

    reasons: list[str] = []
    if deterioration is not None and deterioration >= cfg.payment.deterioration_days:
        reasons.append(f"Payment delay increased from {baseline_avg:.0f} "
                       f"to {recent_avg:.0f} days")
    if bounced:
        reasons.append(f"{bounced} bounced cheque(s)")
    if overdue_ratio >= cfg.payment.overdue_ratio_warning:
        reasons.append(f"{late_count}/{total} payments are late")

    confidence = min(1.0, total / 10.0)

    return signal(
        "payment_behavior", customer_id,
        value=round(median_delay, 2),
        score=round(min(100.0, median_delay), 2),
        status=_STATUS[classification],
        direction=direction,
        confidence=round(confidence, 3),
        sample_size=total,
        evidence={
            "classification": classification,
            "average_delay_days": round(avg_delay, 2),
            "median_delay_days": round(median_delay, 2),
            "max_delay_days": round(max_delay, 2),
            "overdue_amount": round(overdue_amount, 2),
            "overdue_ratio": round(overdue_ratio, 3),
            "late_invoices": late_count,
            "total_payments": total,
            "bounced_cheques": bounced,
            "recent_avg_delay": round(recent_avg, 2) if recent_avg is not None else None,
            "baseline_avg_delay": round(baseline_avg, 2) if baseline_avg is not None else None,
            "deterioration_days": round(deterioration, 2) if deterioration is not None else None,
        },
        reasons=reasons,
    )
