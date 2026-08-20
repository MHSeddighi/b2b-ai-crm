"""Signal 8 — Churn Risk (derived).

Deterministic rules/scoring over the base signals. Correlated purchase
signals (trend / cycle / recency) are grouped so one underlying decline is
not triple-counted, then strong evidence groups are counted to reach a band.
Confidence is the weakest contributing signal — never dragged down by an
irrelevant ``unknown`` signal.
"""
from __future__ import annotations

import datetime as dt

from backend.crm.config import DerivedConfig, SignalConfig
from backend.crm.schemas import CustomerSignal
from backend.crm.signals.base import signal


def _purchase_group(signals: dict[str, CustomerSignal]) -> tuple[float, str, str | None]:
    """trend + cycle describe the same decline -> take the max (no double count)."""
    points, label, src = 0.0, "", None
    trend = signals.get("purchase_trend")
    cycle = signals.get("purchase_cycle")

    if trend is not None:
        if trend.status == "critical":
            points, label, src = 35.0, "Purchase volume declined significantly", "purchase_trend"
        elif trend.status == "warning":
            points, label, src = 25.0, "Purchase volume declining", "purchase_trend"

    if cycle is not None:
        if cycle.status == "critical":
            pts, lbl = 30.0, "Customer is far beyond normal purchase cycle"
        elif cycle.status == "warning":
            pts, lbl = 20.0, "Customer is beyond normal purchase cycle"
        else:
            pts, lbl = 0.0, ""
        if pts > points:
            points, label, src = pts, lbl, "purchase_cycle"

    return points, label, src


def calculate(customer_id: str, signals: dict[str, CustomerSignal],
              ref: dt.date, cfg: SignalConfig) -> CustomerSignal:
    dcfg = cfg.derived
    contributions: list[tuple[str, float, str, str | None]] = []  # (group, points, reason, signal)

    pp, plabel, psrc = _purchase_group(signals)
    if pp > 0:
        contributions.append(("purchase", pp, plabel, psrc))

    complaint = signals.get("complaint_impact")
    if complaint is not None and complaint.status in ("warning", "critical"):
        pts = 25.0 if complaint.status == "critical" else 15.0
        contributions.append(("complaint", pts,
                              "Complaint activity followed by purchase decline",
                              "complaint_impact"))

    payment = signals.get("payment_behavior")
    if payment is not None:
        if payment.status == "critical":
            contributions.append(("payment", 15.0, "Payment behaviour critical",
                                  "payment_behavior"))
        elif payment.status == "warning" or payment.direction == "declining":
            contributions.append(("payment", 8.0, "Payment behaviour deteriorating",
                                  "payment_behavior"))

    sow = signals.get("share_of_wallet")
    if sow is not None and sow.evidence.get("classification") == "low_share":
        contributions.append(("share", 5.0, "Share of wallet is low", "share_of_wallet"))

    total = min(100.0, sum(c[1] for c in contributions))
    strong_groups = sum(1 for c in contributions if c[1] >= 15)

    if strong_groups >= dcfg.churn_critical_groups:
        status = "critical"
    elif strong_groups >= dcfg.churn_high_groups:
        status = "high"
    elif strong_groups >= dcfg.churn_warning_groups:
        status = "warning"
    else:
        status = "low"

    # Confidence from only the signals that actually contributed.
    contrib_confs = [signals[c[3]].confidence for c in contributions
                     if c[3] and c[3] in signals and signals[c[3]] is not None]
    confidence = min(contrib_confs) if contrib_confs else 0.0

    reasons = [c[2] for c in contributions if c[1] > 0]

    return signal(
        "churn_risk", customer_id,
        value=strong_groups,
        score=round(total, 2),
        status=status if status != "low" else "neutral",
        direction="declining" if status in ("high", "critical", "warning") else "stable",
        confidence=round(confidence, 3),
        sample_size=0,
        evidence={
            "level": status,
            "strong_negative_groups": strong_groups,
            "contributions": [
                {"group": g, "points": p, "reason": r}
                for g, p, r, _ in contributions
            ],
        },
        reasons=reasons,
    )
