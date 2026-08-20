"""Signal registry. Base signals are computed from the DB; derived signals
(growth_potential, churn_risk) consume the base signals."""
from __future__ import annotations

from backend.crm.signals import (
    churn_risk,
    complaint_impact,
    dev_request,
    growth_potential,
    margin_trend,
    offer_affinity,
    payment_behavior,
    profit,
    purchase_cycle,
    purchase_trend,
    share_of_wallet,
)

# Signals computed directly from the database, in a stable order.
BASE_SIGNALS = {
    "profit": profit.calculate,
    "purchase_trend": purchase_trend.calculate,
    "payment_behavior": payment_behavior.calculate,
    "share_of_wallet": share_of_wallet.calculate,
    "purchase_cycle": purchase_cycle.calculate,
    "margin_trend": margin_trend.calculate,
    "offer_affinity": offer_affinity.calculate,
    "complaint_impact": complaint_impact.calculate,
    "dev_request": dev_request.calculate,
}

# Derived signals, computed after the base signals exist.
DERIVED_SIGNALS = {
    "growth_potential": growth_potential.calculate,
    "churn_risk": churn_risk.calculate,
}

__all__ = [
    "BASE_SIGNALS",
    "DERIVED_SIGNALS",
    "profit", "purchase_trend", "payment_behavior", "share_of_wallet",
    "purchase_cycle", "margin_trend", "offer_affinity", "complaint_impact",
    "growth_potential", "churn_risk",
]
