"""Tool layer — the five chatbot-facing accessors.

Each returns a JSON string (matching the existing MCP ``query`` tool style).
The LLM may only consume these values; it never computes them.
"""
from __future__ import annotations

import json
from typing import Any

from backend.crm import data
from backend.crm.service import service


def _dump(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, default=str)


def get_customer_signals(customer_id: str) -> str:
    """All calculated signals for a customer (deterministic, backend-owned)."""
    signals = service.get_signals(customer_id)
    return _dump({k: v.model_dump() for k, v in signals.items()})


def get_customer_state(customer_id: str) -> str:
    """Derived customer state dimensions (value/risk/health/opportunity/etc.)."""
    state = service.get_state(customer_id)
    return _dump(state.model_dump() if state else None)


def get_customer_reasons(customer_id: str) -> str:
    """Structured evidence/reasons explaining the important states."""
    reasons = service.get_reasons(customer_id)
    return _dump([r.model_dump() for r in reasons])


def get_next_best_actions(customer_id: str) -> str:
    """Backend-approved, eligible + ranked actions only."""
    actions = service.get_next_best_actions(customer_id)
    return _dump([a.model_dump() for a in actions])


def get_customer_action_plan(customer_id: str) -> str:
    """Complete deterministic recommendation context for one customer."""
    return _dump(service.get_action_plan(customer_id))


def top_at_risk_customers(limit: int = 10) -> str:
    """Rank customers by their REAL churn-risk signal and return the top
    ``limit``.

    For every customer the deterministic engine computes the base signals the
    churn-risk signal consumes (purchase trend/cycle, complaint impact, payment
    behaviour, share of wallet) and derives the churn-risk score — no heuristic
    SQL, no LLM involvement. The ranking is cached under the global data
    fingerprint, so repeat calls are instant until the data changes. Result
    columns: Customer_ID, Customer_Segment, Customer_Status, complaints,
    orders, revenue, last_purchase, days_since_last_purchase, bounced,
    risk_score, risk_level.
    """
    from backend.crm.at_risk import engine_at_risk
    limit = max(1, min(int(limit or 10), 50))
    rows = engine_at_risk(limit)
    cols = ["Customer_ID", "Customer_Segment", "Customer_Status", "complaints",
            "orders", "revenue", "last_purchase", "days_since_last_purchase",
            "bounced", "risk_score", "risk_level"]
    return _dump({
        "columns": cols,
        "rows": [
            [
                r["customer_id"], r["segment"], r["status"], r["complaints"],
                r["orders"], r["revenue"], r["last_purchase"], r["days_since"],
                r["bounced"], r["risk_score"], r["risk_level"],
            ]
            for r in rows
        ],
        "n_rows": len(rows),
    })
