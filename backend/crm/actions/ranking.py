"""Action priority ranking.

priority = business_impact × urgency × confidence × data_quality

Deterministic and configurable: business impact is declared per action, urgency
comes from the driving signal's severity, confidence from the weakest
contributing signal, and data quality from the engine's overall assessment.
"""
from __future__ import annotations

from backend.crm.actions.definitions import get_meta
from backend.crm.schemas import ActionDefinition, CustomerSignal, CustomerState

_STATUS_URGENCY = {
    "critical": 1.0, "warning": 0.7, "positive": 0.6,
    "neutral": 0.3, "unknown": 0.1,
    # state statuses
    "high": 0.8, "poor": 0.8, "medium": 0.5, "low": 0.2, "healthy": 0.2,
}


def _urgency(action: ActionDefinition, signals: dict[str, CustomerSignal],
             state: CustomerState) -> float:
    meta = get_meta(action.action_id)
    ids = meta.get("urgency_signals", [])
    if not ids:
        return 0.3
    vals = []
    for sid in ids:
        sig = signals.get(sid)
        if sig is not None:
            vals.append(_STATUS_URGENCY.get(sig.status, 0.3))
    return max(vals) if vals else 0.3


def _confidence(action: ActionDefinition, signals: dict[str, CustomerSignal]) -> float:
    meta = get_meta(action.action_id)
    ids = meta.get("confidence_signals", [])
    if not ids:
        return 0.5
    vals = [signals[i].confidence for i in ids
            if i in signals and signals[i] is not None]
    return min(vals) if vals else 0.5


def compute_priority(action: ActionDefinition,
                     signals: dict[str, CustomerSignal],
                     state: CustomerState,
                     data_quality: float) -> tuple[float, float]:
    meta = get_meta(action.action_id)
    impact = meta.get("business_impact", 0.5)
    urgency = _urgency(action, signals, state)
    confidence = _confidence(action, signals)
    dq = max(0.0, min(1.0, data_quality))

    priority = impact * urgency * confidence * dq
    return round(priority, 4), round(confidence, 4)
