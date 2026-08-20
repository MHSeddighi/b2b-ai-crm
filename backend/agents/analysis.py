"""Deterministic helpers for copilot block analysis.

These functions encode business rules the LLM must NOT violate, so the agent
can compute correct numbers without relying on the model. They are unit-tested.
"""
from __future__ import annotations

from typing import Any

# A query whose result exceeds this many rows is "too huge" to analyse inline.
HUGE_RESULT_THRESHOLD = 100
# How many result rows we are willing to inline into an LLM prompt for reasoning.
MAX_INLINE_ROWS = 50


def is_huge(n_rows: int) -> bool:
    """Whether a result is too large to analyse inline."""
    return n_rows > HUGE_RESULT_THRESHOLD


def too_huge_message(n_rows: int) -> str:
    return (
        f"نتیجه شامل {n_rows:,} ردیف است که برای تحلیل مستقیم بسیار بزرگ است. "
        "می‌توانم داده را خلاصه، فیلتر یا به‌صورت نمونه تحلیل کنم — بگویید کدام را می‌خواهید."
    )


def order_count(rows: list[list[Any]], order_idx: int) -> int:
    """Count DISTINCT orders, guarding against multi-line double counting."""
    return len({r[order_idx] for r in rows if r[order_idx] is not None})


def quantity_sum(rows: list[list[Any]], qty_idx: int) -> float:
    """Total units sold (SUM of quantity), distinct from order count."""
    total = 0.0
    for r in rows:
        v = r[qty_idx]
        if v is None:
            continue
        try:
            total += float(v)
        except (TypeError, ValueError):
            continue
    return total


def dedupe_order_lines(rows: list[list[Any]], line_id_idx: int) -> list[list[Any]]:
    """Drop duplicate rows by a unique line id after a join.

    Null line ids are kept as-is (never dropped) to avoid losing data.
    """
    seen: set[Any] = set()
    out: list[list[Any]] = []
    for r in rows:
        key = r[line_id_idx]
        if key is None:
            out.append(r)
            continue
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out


def column_index(columns: list[str], keys: list[str]) -> int | None:
    """Find the index of a column by one of several candidate names."""
    for c, k in enumerate(columns):
        if k in keys:
            return c
    return None
