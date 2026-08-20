"""Derived customer state (multiple dimensions, NOT one universal score)."""
from __future__ import annotations

from backend.crm.schemas import CustomerSignal, CustomerState, StateDimension


def _dim(score: float | None, status: str, confidence: float,
         reasons: list[str], evidence: dict) -> StateDimension:
    return StateDimension(score=score, status=status, confidence=confidence,
                          reasons=reasons, evidence=evidence)


def _clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, v))


def build_state(customer_id: str, signals: dict[str, CustomerSignal]) -> CustomerState:
    s = signals

    # --- profitability (from real profit) ---
    profit = s.get("profit")
    if profit is not None and profit.status not in ("unknown", "low_confidence"):
        profitability = _dim(
            score=_clamp(profit.score or 0.0),
            status=profit.status,
            confidence=profit.confidence,
            reasons=list(profit.reasons),
            evidence=dict(profit.evidence),
        )
    elif profit is not None and profit.status == "low_confidence":
        profitability = _dim(
            score=_clamp(profit.score or 0.0),
            status="unknown",
            confidence=profit.confidence,
            reasons=list(profit.reasons),
            evidence=dict(profit.evidence),
        )
    else:
        profitability = _dim(None, "unknown", 0.0, [], {})

    # --- churn risk ---
    churn = s.get("churn_risk")
    churn_risk = _dim(
        score=churn.score if churn else None,
        status=churn.status if churn else "unknown",
        confidence=churn.confidence if churn else 0.0,
        reasons=list(churn.reasons) if churn else [],
        evidence=dict(churn.evidence) if churn else {},
    )

    # --- growth opportunity ---
    growth = s.get("growth_potential")
    growth_opportunity = _dim(
        score=growth.score if growth else None,
        status=growth.status if growth else "unknown",
        confidence=growth.confidence if growth else 0.0,
        reasons=list(growth.reasons) if growth else [],
        evidence=dict(growth.evidence) if growth else {},
    )

    # --- value (revenue scale, tempered by margin trustworthiness) ---
    import math
    if profit is not None and profit.evidence.get("total_revenue"):
        revenue = float(profit.evidence["total_revenue"])
        if revenue > 0:
            rev_score = min(100.0, 20.0 * math.log10(revenue + 1.0))
            value_status = ("high" if rev_score >= 70
                            else ("medium" if rev_score >= 50 else "low"))
            # A trusted negative margin caps value regardless of revenue.
            if profit.status in ("positive", "neutral", "warning", "critical") \
                    and profit.evidence.get("classification") == "negative_profit":
                value_status = "low"
                rev_score = min(rev_score, 30.0)
            value = _dim(
                score=round(rev_score, 2), status=value_status,
                confidence=profit.confidence,
                reasons=[f"Total revenue {revenue:,.0f}",
                         f"Profit margin {profit.evidence.get('profit_margin', 0):.1%}"],
                evidence={"total_revenue": revenue,
                          "real_profit": profit.evidence.get("real_profit"),
                          "profit_margin": profit.evidence.get("profit_margin"),
                          "cost_coverage": profit.evidence.get("cost_coverage")},
            )
        else:
            value = _dim(None, "unknown", 0.0, [], {})
    else:
        value = _dim(None, "unknown", 0.0, [], {})

    # --- payment risk (inverse of payment behaviour) ---
    payment = s.get("payment_behavior")
    if payment is not None and payment.status != "unknown":
        risk_status = {"positive": "low", "neutral": "low",
                       "warning": "warning", "critical": "critical"}[payment.status]
        payment_risk = _dim(
            score=payment.score,
            status=risk_status,
            confidence=payment.confidence,
            reasons=list(payment.reasons),
            evidence=dict(payment.evidence),
        )
    else:
        payment_risk = _dim(None, "unknown", 0.0, [], {})

    # --- relationship health (complaint + payment + offer affinity) ---
    relationship_health = _relationship_health(s)

    return CustomerState(
        customer_id=customer_id,
        value=value,
        churn_risk=churn_risk,
        growth_opportunity=growth_opportunity,
        relationship_health=relationship_health,
        profitability=profitability,
        payment_risk=payment_risk,
    )


def _relationship_health(signals: dict[str, CustomerSignal]) -> StateDimension:
    score = 50.0
    reasons: list[str] = []
    contributing: list[str] = []

    complaint = signals.get("complaint_impact")
    if complaint is not None and complaint.sample_size > 0:
        contributing.append("complaint_impact")
        if complaint.status == "critical":
            score -= 30
            reasons.append("Severe complaint impact")
        elif complaint.status == "warning":
            score -= 15
            reasons.append("Complaint impact warning")
    if complaint is not None and complaint.evidence.get("unresolved_count"):
        score -= 10
        reasons.append(f"{complaint.evidence['unresolved_count']} unresolved complaint(s)")

    payment = signals.get("payment_behavior")
    if payment is not None and (payment.direction == "declining"
                                or payment.status in ("warning", "critical")):
        contributing.append("payment_behavior")
        score -= 10
        reasons.append("Payment behaviour deteriorating")

    affinity = signals.get("offer_affinity")
    if affinity is not None and affinity.status == "positive":
        contributing.append("offer_affinity")
        score += 5

    score = _clamp(score)
    status = "healthy" if score >= 70 else ("warning" if score >= 40 else "poor")

    confidences = [signals[i].confidence for i in contributing
                   if i in signals and signals[i] is not None]
    confidence = min(confidences) if confidences else 0.0

    return _dim(round(score, 2), status, round(confidence, 3), reasons, {"base": 50})
