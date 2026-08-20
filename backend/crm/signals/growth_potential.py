"""Signal 7 — Growth Potential (derived).

Identifies customers where additional business is *plausible*: low share of
wallet + healthy purchase activity + good payment + acceptable profitability.
Not an arbitrary score — every point is backed by a concrete signal.
"""
from __future__ import annotations

import datetime as dt

from backend.crm.config import SignalConfig
from backend.crm.schemas import CustomerSignal
from backend.crm.signals.base import signal


def calculate(customer_id: str, signals: dict[str, CustomerSignal],
              ref: dt.date, cfg: SignalConfig) -> CustomerSignal:
    sow = signals.get("share_of_wallet")
    trend = signals.get("purchase_trend")
    payment = signals.get("payment_behavior")
    profit = signals.get("profit")

    score = 0.0
    reasons: list[str] = []
    contributing: list[str] = []

    def sow_status() -> str:
        return (sow.evidence.get("classification") if sow else None) or ""

    # 1. Share of wallet — the headroom.
    if sow is not None and sow.evidence.get("classification") == "low_share":
        score += 40
        contributing.append("share_of_wallet")
        reasons.append(f"Estimated share of wallet is only "
                       f"{sow.evidence.get('share_pct', '?')}%")
    elif sow is not None and sow.evidence.get("classification") == "medium_share":
        score += 15
        contributing.append("share_of_wallet")

    # 2. Purchase activity health.
    if trend is not None and trend.status != "unknown":
        contributing.append("purchase_trend")
        if trend.status == "positive":
            score += 25
            reasons.append("Customer has strong purchase activity")
        elif trend.status == "neutral":
            score += 10
        elif trend.status in ("warning", "critical"):
            score -= 30

    # 3. Payment behaviour.
    if payment is not None and payment.status != "unknown":
        contributing.append("payment_behavior")
        if payment.status == "positive":
            score += 20
            reasons.append("Payment behaviour is healthy")
        elif payment.status in ("warning", "critical"):
            score -= 20

    # 4. Profitability acceptable.
    if profit is not None and profit.status not in ("unknown", "low_confidence"):
        contributing.append("profit")
        cls = profit.evidence.get("classification")
        if cls in ("high_profit", "normal_profit"):
            score += 15
            reasons.append("Customer remains profitable")
        elif cls == "negative_profit":
            score -= 25

    score = max(0.0, min(100.0, score))

    if score >= 60:
        status = "high"
    elif score >= 35:
        status = "medium"
    else:
        status = "low"

    confidence = _min_confidence(signals, contributing)

    return signal(
        "growth_potential", customer_id,
        value=None,
        score=round(score, 2),
        status="positive" if status == "high" else "neutral",
        direction="improving" if status == "high" else "stable",
        confidence=round(confidence, 3),
        sample_size=0,
        evidence={"level": status, "components": {
            "share_of_wallet_low": sow is not None and sow.evidence.get("classification") == "low_share",
            "purchase_healthy": trend is not None and trend.status == "positive",
            "payment_good": payment is not None and payment.status == "positive",
            "profitable": profit is not None and profit.evidence.get("classification")
                          in ("high_profit", "normal_profit"),
        }},
        reasons=reasons,
    )


def _min_confidence(signals: dict[str, CustomerSignal], ids: list[str]) -> float:
    vals = [signals[i].confidence for i in ids
            if i in signals and signals[i] is not None]
    if not vals:
        return 0.0
    # Use the weakest contributing confidence so we never overclaim.
    return min(vals)
