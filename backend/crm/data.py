"""Read-only DuckDB data access + shared aggregation helpers for the engine.

Each signal receives a live connection (opened once per customer by the
engine) and a reference "as of" date so every signal agrees on what "now"
means. All queries are plain SELECTs — no writes, no external access.
"""
from __future__ import annotations

import datetime as dt
from typing import Any

import duckdb

from backend.config import settings


def connect(read_only: bool = True) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(str(settings.db_path), read_only=read_only)
    con.execute("SET enable_external_access=false")
    return con


def reference_date(con: duckdb.DuckDBPyConnection) -> dt.date:
    """The dataset's latest sale date acts as 'now' for recency signals."""
    mx = con.execute('SELECT MAX("تاریخ") FROM sales').fetchone()[0]
    if mx:
        return as_date(mx)
    return dt.date.today()


def as_date(value: Any) -> dt.date:
    if isinstance(value, dt.date):
        return value
    if isinstance(value, dt.datetime):
        return value.date()
    if value is None:
        raise ValueError("null date")
    return dt.date.fromisoformat(str(value)[:10])


def customer_exists(con: duckdb.DuckDBPyConnection, customer_id: str) -> bool:
    return con.execute(
        "SELECT 1 FROM customers WHERE Customer_ID = ?", [customer_id]
    ).fetchone() is not None


def one(con: duckdb.DuckDBPyConnection, sql: str,
        params: list[Any] | None = None) -> tuple | None:
    return con.execute(sql, params or []).fetchone()


def rows(con: duckdb.DuckDBPyConnection, sql: str,
         params: list[Any] | None = None) -> list[tuple]:
    return con.execute(sql, params or []).fetchall()


def safefloat(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def safedate(v: Any) -> dt.date | None:
    if v is None:
        return None
    try:
        return as_date(v)
    except (ValueError, TypeError):
        return None


def window_bounds(ref: dt.date, days: int) -> tuple[str, str]:
    """Inclusive [start, end] ISO date strings for a trailing ``days`` window."""
    end = ref
    start = end - dt.timedelta(days=days - 1)
    return start.isoformat(), end.isoformat()


def pct_change(current: float | None, previous: float | None) -> float | None:
    """Relative change (current-previous)/previous; None if baseline is 0/missing."""
    if current is None or previous is None or previous == 0:
        return None
    return (current - previous) / previous
