"""Action eligibility evaluation.

Interprets the declarative condition dicts from ``definitions.py`` against the
computed signals + state. Eligibility is checked BEFORE ranking, and forbidden
conditions always override an otherwise-eligible action.
"""
from __future__ import annotations

from typing import Any

from backend.crm.schemas import ActionDefinition, CustomerSignal, CustomerState


def _signal(signals: dict[str, CustomerSignal], sid: str) -> CustomerSignal | None:
    return signals.get(sid)


def _eval_condition(cond: dict[str, Any],
                    signals: dict[str, CustomerSignal],
                    state: CustomerState) -> bool:
    if "signal" in cond:
        sig = _signal(signals, cond["signal"])
        if sig is None:
            return False
        if "status" in cond:
            if sig.status not in cond["status"]:
                return False
        if "score_ge" in cond:
            if sig.score is None or sig.score < cond["score_ge"]:
                return False
        if "score_le" in cond:
            if sig.score is None or sig.score > cond["score_le"]:
                return False
        if "evidence_ge" in cond:
            for k, v in cond["evidence_ge"].items():
                ev = sig.evidence.get(k)
                if ev is None or ev < v:
                    return False
        return True

    if "state" in cond:
        dim = getattr(state, cond["state"], None)
        if dim is None:
            return False
        if "status" in cond:
            if dim.status not in cond["status"]:
                return False
        if "score_ge" in cond:
            if dim.score is None or dim.score < cond["score_ge"]:
                return False
        if "score_le" in cond:
            if dim.score is None or dim.score > cond["score_le"]:
                return False
        return True

    raise ValueError(f"Unknown condition shape: {cond!r}")


def _eval_group(group: dict[str, Any],
                signals: dict[str, CustomerSignal],
                state: CustomerState) -> bool:
    """A group matches when every 'all' condition AND at least one 'any'
    condition holds (an empty list is trivially satisfied)."""
    for cond in group.get("all", []):
        if not _eval_condition(cond, signals, state):
            return False
    any_conds = group.get("any", [])
    if any_conds and not any(_eval_condition(c, signals, state) for c in any_conds):
        return False
    return True


def is_eligible(action: ActionDefinition,
                signals: dict[str, CustomerSignal],
                state: CustomerState) -> tuple[bool, list[str]]:
    """Return (eligible, blocked_reasons). Forbidden always wins."""
    blocked: list[str] = []
    if action.forbidden and _eval_group(action.forbidden, signals, state):
        blocked.append(f"Forbidden condition triggered ({action.action_id})")
    if not _eval_group(action.eligibility, signals, state):
        return False, blocked
    if blocked:
        return False, blocked
    return True, []
