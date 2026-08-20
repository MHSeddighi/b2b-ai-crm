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


# ---------------------------------------------------------------------------
# Discriminator ranking
#
# Handed several comparison numbers, a weaker LLM tends to latch onto the
# first one or two it sees and conclude "they are similar" — which is not a
# finding and gives the user nothing to act on. Rather than hoping the model
# eyeballs the rows correctly, we compute HERE, deterministically, which
# features actually differ between the compared classes and by how much, and
# hand the prompt a ranked answer. Similar features are reported explicitly as
# ruled out so the model stops presenting them as insights.
# ---------------------------------------------------------------------------

# Relative gap at or above which a feature counts as genuinely different.
MEANINGFUL_REL_DIFF = 0.10

# Above this many rows a result is a ranked list of entities (top customers,
# all order lines), not a class comparison. Contrasting its extremes would be
# meaningless noise ("customer #500 differs from customer #1"), so skip it.
MAX_DISCRIMINATOR_ROWS = 25


def _to_num(v: Any) -> float | None:
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(str(v).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def _rel_diff(a: float, b: float) -> float:
    hi = max(abs(a), abs(b))
    return abs(a - b) / hi if hi else 0.0


def _label_index(columns: list[str], rows: list[list[Any]]) -> int | None:
    """Index of the column naming the class/category (first all-text column)."""
    for i in range(len(columns)):
        vals = [r[i] for r in rows if i < len(r)]
        if vals and all(v is not None and _to_num(v) is None for v in vals):
            return i
    return None


def rank_discriminators(
    columns: list[str],
    rows: list[list[Any]],
    max_out: int = 8,
) -> str:
    """Rank which columns actually separate the compared classes.

    Returns a plain-text summary (or "" when the result isn't a comparison):
    features are split into those that genuinely differ and those that are
    effectively identical, each with the measured gap.
    """
    if not columns or not rows or len(rows) < 2:
        return ""
    if len(rows) > MAX_DISCRIMINATOR_ROWS:
        return ""
    li = _label_index(columns, rows)
    if li is None:
        return ""
    num_idx = [
        i for i in range(len(columns))
        if i != li and any(_to_num(r[i]) is not None for r in rows if i < len(r))
    ]
    if not num_idx:
        return ""

    diffs: list[tuple[float, str]] = []

    if len(rows) == 2:
        # Two classes side by side: compare each metric between them.
        a, b = rows[0], rows[1]
        la, lb = str(a[li]), str(b[li])
        for i in num_idx:
            va, vb = _to_num(a[i]), _to_num(b[i])
            if va is None or vb is None:
                continue
            diffs.append(
                (_rel_diff(va, vb), f"{columns[i]}: {va:,.4g} ({la}) vs {vb:,.4g} ({lb})")
            )
    elif len(num_idx) == 2:
        # Per-category counts for two classes: compare each category's SHARE,
        # so a class with more rows overall doesn't dominate every category.
        ia, ib = num_idx
        ta = sum(_to_num(r[ia]) or 0 for r in rows) or 1
        tb = sum(_to_num(r[ib]) or 0 for r in rows) or 1
        for r in rows:
            sa = (_to_num(r[ia]) or 0) / ta
            sb = (_to_num(r[ib]) or 0) / tb
            diffs.append((
                abs(sa - sb),
                f"{r[li]}: {sa * 100:.1f}% of {columns[ia]} vs {sb * 100:.1f}% of {columns[ib]}",
            ))
    else:
        # One metric across many categories: contrast the extremes.
        for i in num_idx:
            vals = sorted(
                (_to_num(r[i]), str(r[li])) for r in rows if _to_num(r[i]) is not None
            )
            if len(vals) < 2:
                continue
            lo, hi = vals[0], vals[-1]
            diffs.append(
                (_rel_diff(hi[0], lo[0]),
                 f"{columns[i]}: {hi[0]:,.4g} ({hi[1]}) vs {lo[0]:,.4g} ({lo[1]})")
            )

    if not diffs:
        return ""

    diffs.sort(key=lambda d: d[0], reverse=True)
    big = [d for d in diffs if d[0] >= MEANINGFUL_REL_DIFF][:max_out]
    small = [d for d in diffs if d[0] < MEANINGFUL_REL_DIFF][:max_out]

    out: list[str] = []
    if big:
        out.append("FEATURES THAT ACTUALLY DIFFER (lead with these — biggest gap first):")
        out += [f"  * {t} -> {p * 100:.0f}% gap" for p, t in big]
    if small:
        out.append("ESSENTIALLY IDENTICAL (ruled out — do NOT present these as a finding):")
        out += [f"  * {t} -> {p * 100:.1f}% gap" for p, t in small]
    return "\n".join(out)
