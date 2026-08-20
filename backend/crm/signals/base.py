"""Shared helpers for signal calculation."""
from __future__ import annotations

from typing import Any

from backend.crm.schemas import CustomerSignal


def signal(signal_id: str, customer_id: str, **kwargs: Any) -> CustomerSignal:
    return CustomerSignal(signal_id=signal_id, customer_id=customer_id, **kwargs)


def normalize_score(value: float | None, lo: float = 0.0,
                    hi: float = 100.0) -> float | None:
    """Clamp a raw score into [lo, hi]; None stays None."""
    if value is None:
        return None
    return max(lo, min(hi, value))


def _band(value: float | None, bounds: tuple[tuple[float, str], ...],
          default: str) -> str:
    """Classify ``value`` by ordered thresholds. First matching (value < bound)
    band wins; otherwise ``default``."""
    if value is None:
        return "unknown"
    for threshold, label in bounds:
        if value < threshold:
            return label
    return default


# Status + direction are both derived from the same numeric signal; these
# helpers keep the classification logic in one place and testable.
def classify_positive_negative(value: float | None,
                               positive_threshold: float,
                               negative_threshold: float) -> str:
    """Map a signed metric (higher = better) to positive/neutral/warning/critical."""
    if value is None:
        return "unknown"
    if value >= positive_threshold:
        return "positive"
    if value <= negative_threshold:
        return "critical"
    return "neutral"


def round2(v: float | None) -> float | None:
    return round(v, 2) if v is not None else None
