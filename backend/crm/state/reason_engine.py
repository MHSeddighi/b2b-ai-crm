"""Reason / evidence layer: structured reasons derived from signals.

Each reason is independently citable (reason_id, evidence, source signals), so
the decision engine and the UI can explain *why* without calling the LLM.
"""
from __future__ import annotations

from backend.crm.schemas import CustomerSignal, Reason


def build_reasons(signals: dict[str, CustomerSignal]) -> list[Reason]:
    reasons: list[Reason] = []

    def add(reason_id: str, type_: str, severity: str, confidence: float,
            evidence: dict, sources: list[str]) -> None:
        reasons.append(Reason(
            reason_id=reason_id, type=type_, severity=severity,
            confidence=round(confidence, 3), evidence=evidence,
            source_signals=sources,
        ))

    trend = signals.get("purchase_trend")
    if trend is not None and trend.status in ("warning", "critical"):
        add("PURCHASE_DECLINING", "PURCHASE_DECLINING",
            "critical" if trend.status == "critical" else "warning",
            trend.confidence, dict(trend.evidence), ["purchase_trend"])

    cycle = signals.get("purchase_cycle")
    if cycle is not None and cycle.status in ("warning", "critical"):
        add("PURCHASE_CYCLE_DELAYED", "PURCHASE_CYCLE_DELAYED",
            cycle.status, cycle.confidence, dict(cycle.evidence), ["purchase_cycle"])

    payment = signals.get("payment_behavior")
    if payment is not None and (payment.status in ("warning", "critical")
                                or payment.direction == "declining"):
        add("PAYMENT_DETERIORATING", "PAYMENT_DETERIORATING",
            payment.status if payment.status in ("warning", "critical") else "warning",
            payment.confidence, dict(payment.evidence), ["payment_behavior"])
    if payment is not None and payment.status == "critical":
        add("HIGH_CREDIT_RISK", "HIGH_CREDIT_RISK", "critical",
            payment.confidence, dict(payment.evidence), ["payment_behavior"])

    profit = signals.get("profit")
    if profit is not None and profit.evidence.get("classification") in ("high_profit", "normal_profit"):
        add("HIGH_PROFIT", "HIGH_PROFIT", "positive", profit.confidence,
            dict(profit.evidence), ["profit"])
    if profit is not None and profit.evidence.get("classification") == "negative_profit":
        add("LOW_MARGIN", "LOW_MARGIN", "warning", profit.confidence,
            dict(profit.evidence), ["profit"])

    growth = signals.get("growth_potential")
    if growth is not None and growth.evidence.get("level") == "high":
        add("HIGH_GROWTH_POTENTIAL", "HIGH_GROWTH_POTENTIAL", "positive",
            growth.confidence, dict(growth.evidence), ["growth_potential"])

    complaint = signals.get("complaint_impact")
    if complaint is not None and complaint.status in ("warning", "critical"):
        add("COMPLAINT_FOLLOWED_BY_DECLINE", "COMPLAINT_FOLLOWED_BY_DECLINE",
            complaint.status, complaint.confidence,
            dict(complaint.evidence), ["complaint_impact"])

    affinity = signals.get("offer_affinity")
    if affinity is not None and affinity.evidence.get("response_rate") is not None:
        rate = affinity.evidence["response_rate"]
        if rate < 0.5 and affinity.sample_size >= 3:
            add("OFFER_FATIGUE", "OFFER_FATIGUE", "warning", affinity.confidence,
                dict(affinity.evidence), ["offer_affinity"])

    # Sort by severity weight so the most important reasons lead.
    order = {"critical": 0, "warning": 1, "neutral": 2, "positive": 3}
    reasons.sort(key=lambda r: order.get(r.severity, 2))
    return reasons
