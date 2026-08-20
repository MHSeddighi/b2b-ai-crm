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
    """Rank customers by churn-risk and return the top ``limit``.

    Computed deterministically in a single SQL pass over the same signals the
    deterministic engine uses: complaint volume, purchase recency (days since
    the last purchase), order volume, and bounced checks. The LLM must NOT
    recompute or alter these scores. The result includes richer customer
    context (segment, status, revenue, days since last purchase) so the answer
    can be grounded in plain business facts, not just a score.
    """
    limit = max(1, min(int(limit or 10), 50))
    con = data.connect()
    try:
        ref = data.reference_date(con)
        ref_lit = f"DATE '{ref.isoformat()}'"
        sql = f"""
        WITH agg AS (
          SELECT
            c.Customer_ID,
            c.Customer_Segment,
            c.Customer_Status,
            c.Credit_Limit,
            c.Payment_Terms_Days,
            (SELECT COUNT(*) FROM complaints co
              WHERE co.Customer_ID = c.Customer_ID) AS complaints,
            (SELECT MAX(CAST(s."تاریخ" AS DATE)) FROM sales s
              WHERE s.Customer_ID = c.Customer_ID) AS last_purchase,
            (SELECT COUNT(DISTINCT s."شماره فاکتور") FROM sales s
              WHERE s.Customer_ID = c.Customer_ID) AS orders,
            (SELECT COALESCE(SUM(s."مبلغ کل"), 0) FROM sales s
              WHERE s.Customer_ID = c.Customer_ID) AS revenue,
            (SELECT COUNT(*) FROM collections col
              WHERE col.Customer_ID = c.Customer_ID
                AND col."چک برگشتی" = 'بله') AS bounced
          FROM customers c
        )
        SELECT
          Customer_ID,
          Customer_Segment,
          Customer_Status,
          complaints,
          orders,
          revenue,
          last_purchase,
          CAST({ref_lit} - last_purchase AS INT) AS days_since_last_purchase,
          bounced,
          CAST(LEAST(99,
            12
            + LEAST(45, complaints * 8)
            + CASE WHEN last_purchase IS NULL THEN 40
                   WHEN last_purchase < {ref_lit} - INTERVAL 365 DAY THEN 20
                   WHEN last_purchase < {ref_lit} - INTERVAL 180 DAY THEN 10
                   ELSE 0 END
            + CASE WHEN orders = 0 THEN 25 ELSE 0 END
            + LEAST(15, bounced * 10)
          ) AS INT) AS risk_score
        FROM agg
        ORDER BY risk_score DESC, Customer_ID
        LIMIT {limit}
        """
        rows = con.execute(sql).fetchall()
        cols = [d[0] for d in con.description]
    finally:
        con.close()
    return _dump({"columns": cols, "rows": rows, "n_rows": len(rows)})
