"""Next Best Action engine: eligibility -> ranking -> top actions."""
from __future__ import annotations

from backend.crm.actions import eligibility, ranking
from backend.crm.actions.definitions import ACTIONS, get_meta
from backend.crm.schemas import (
    CustomerSignal,
    CustomerState,
    RecommendedAction,
)

MAX_ACTIONS = 3


def _reason(action, signals: dict[str, CustomerSignal]) -> str:
    """Build a deterministic (non-LLM) reason from driving-signal reasons."""
    meta = get_meta(action.action_id)
    parts: list[str] = []
    for sid in meta.get("urgency_signals", []):
        sig = signals.get(sid)
        if sig and sig.reasons:
            parts.append(sig.reasons[0])
    if parts:
        return "; ".join(parts[:3])
    return action.description


def recommend(signals: dict[str, CustomerSignal],
              state: CustomerState,
              data_quality: float,
              limit: int | None = None) -> list[RecommendedAction]:
    eligible: list = []
    blocked_by_forbidden: dict[str, list[str]] = {}

    for action in ACTIONS:
        ok, blocked = eligibility.is_eligible(action, signals, state)
        if ok:
            eligible.append(action)
        elif blocked:
            blocked_by_forbidden[action.action_id] = blocked

    # NO_ACTION is the fallback when nothing else is eligible.
    if not eligible:
        eligible = [a for a in ACTIONS if a.action_id == "NO_ACTION"]

    ranked = []
    for action in eligible:
        priority, confidence = ranking.compute_priority(
            action, signals, state, data_quality)
        ranked.append((priority, confidence, action))

    ranked.sort(key=lambda t: (-t[0], t[2].action_id))
    top = ranked[: limit if limit is not None else MAX_ACTIONS]

    out: list[RecommendedAction] = []
    for priority, confidence, action in top:
        meta = get_meta(action.action_id)
        evidence = []
        for sid in meta.get("urgency_signals", []):
            sig = signals.get(sid)
            if sig and sig.reasons:
                evidence.extend(sig.reasons[:2])
        out.append(RecommendedAction(
            action_id=action.action_id,
            name=action.name,
            category=action.category,
            priority=priority,
            confidence=confidence,
            reason=_reason(action, signals),
            evidence=list(dict.fromkeys(evidence)),
            suggested_next_step=meta.get("next_step", ""),
            blocked_actions=[a for a in blocked_by_forbidden
                             if a != action.action_id],
        ))
    return out
