"""Signal 9 — Complaint Impact.

Measures what happened to purchases *after* complaints (observational, not
causal). Wording stays association-based: "decline followed the complaint",
never "the complaint caused the decline".
"""
from __future__ import annotations

import datetime as dt

import duckdb

from backend.crm.config import ComplaintImpactConfig, SignalConfig
from backend.crm.data import as_date, pct_change, safefloat
from backend.crm.schemas import CustomerSignal
from backend.crm.signals.base import signal


_COMPLAINTS_SQL = """
SELECT "Created_At", "Severity", "Complaint_Status", "Resolved_At", "گروه کالا"
FROM complaints
WHERE Customer_ID = ?
ORDER BY "Created_At" DESC
"""

_SALES_WINDOW_SQL = """
SELECT
    COALESCE(SUM(CASE WHEN "تاریخ" >= ? AND "تاریخ" < ? THEN "مبلغ کل" END), 0) AS before_rev,
    COALESCE(SUM(CASE WHEN "تاریخ" >= ? AND "تاریخ" <= ? THEN "مبلغ کل" END), 0) AS after_rev,
    COUNT(DISTINCT CASE WHEN "تاریخ" >= ? AND "تاریخ" < ? THEN "شماره فاکتور" END) AS before_orders,
    COUNT(DISTINCT CASE WHEN "تاریخ" >= ? AND "تاریخ" <= ? THEN "شماره فاکتور" END) AS after_orders
FROM sales
WHERE Customer_ID = ?
"""

_RESOLVED_STATUSES = {"بسته\u200cشده", "ردشده"}


def _max_severity(complaints: list[tuple], cfg: ComplaintImpactConfig) -> float:
    return max((cfg.severity_weight.get(c[1], 1.0) for c in complaints), default=0.0)


def calculate(con: duckdb.DuckDBPyConnection, customer_id: str,
              ref: dt.date, cfg: SignalConfig) -> CustomerSignal:
    complaints = con.execute(_COMPLAINTS_SQL, [customer_id]).fetchall()

    if not complaints:
        return signal("complaint_impact", customer_id, status="unknown",
                      confidence=0.0, sample_size=0,
                      reasons=["No complaints on record"])

    unresolved = [c for c in complaints if c[2] not in _RESOLVED_STATUSES]
    severity = _max_severity(complaints, cfg.complaint_impact)

    anchor = as_date(complaints[0][0])
    before_s = (anchor - dt.timedelta(days=cfg.time.complaint_before_days)).isoformat()
    after_e = (anchor + dt.timedelta(days=cfg.time.complaint_after_days)).isoformat()
    anchor_s = anchor.isoformat()

    row = con.execute(
        _SALES_WINDOW_SQL,
        [before_s, anchor_s, anchor_s, after_e, before_s, anchor_s, anchor_s, after_e,
         customer_id],
    ).fetchone()

    before_rev = safefloat(row[0]) or 0.0
    after_rev = safefloat(row[1]) or 0.0
    before_orders = int(row[2] or 0)
    after_orders = int(row[3] or 0)

    if before_rev <= 0 or before_orders == 0:
        return signal("complaint_impact", customer_id, status="unknown",
                      confidence=0.0, sample_size=len(complaints),
                      reasons=["No pre-complaint purchase baseline to compare"])

    rev_change = pct_change(after_rev, before_rev)
    order_change = pct_change(float(after_orders), float(before_orders))

    # Association, never causation.
    if rev_change is not None and rev_change <= cfg.complaint_impact.decline_critical:
        classification, status = "severe_decline", "critical"
    elif rev_change is not None and rev_change <= cfg.complaint_impact.decline_warning:
        classification, status = "decline", "warning"
    elif rev_change is not None and rev_change >= 0:
        classification, status = "no_decline", "neutral"
    else:
        classification, status = "mild_decline", "neutral"

    # Escalate when severe + unresolved complaints remain.
    if status != "critical" and unresolved and severity >= 2.0 and rev_change is not None \
            and rev_change <= cfg.complaint_impact.decline_warning:
        status = "critical"

    days_since_complaint = (ref - anchor).days
    recovery = None
    if rev_change is not None and rev_change < 0:
        recovery = f"No recovery after {max(days_since_complaint, 0)} days"

    reasons: list[str] = []
    if rev_change is not None:
        reasons.append(f"Purchase decline ({rev_change:.0%}) followed the complaint")
    if unresolved:
        reasons.append(f"{len(unresolved)} unresolved complaint(s) remain")
    if recovery:
        reasons.append(recovery)

    confidence = min(1.0, len(complaints) / 3.0)

    return signal(
        "complaint_impact", customer_id,
        value=round(rev_change, 4) if rev_change is not None else None,
        score=round(abs(min(0.0, rev_change or 0.0)) * 100, 2),
        status=status,
        direction="declining" if (rev_change is not None and rev_change < 0) else "stable",
        confidence=round(confidence, 3),
        sample_size=len(complaints),
        evidence={
            "classification": classification,
            "complaint_count": len(complaints),
            "unresolved_count": len(unresolved),
            "max_severity": severity,
            "purchase_change_after_complaint": round(rev_change, 4) if rev_change is not None else None,
            "order_change_after_complaint": round(order_change, 4) if order_change is not None else None,
            "before_revenue": round(before_rev, 2),
            "after_revenue": round(after_rev, 2),
            "time_to_recovery": recovery,
            "days_since_complaint": days_since_complaint,
        },
        reasons=reasons,
    )
