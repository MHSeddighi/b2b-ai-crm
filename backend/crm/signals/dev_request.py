"""Auxiliary signal — open product development requests.

Not one of the ten MVP signals; a small grounding signal so the
PRODUCT_DEVELOPMENT_FOLLOWUP action never fires without real evidence.
"""
from __future__ import annotations

import datetime as dt

import duckdb

from backend.crm.config import SignalConfig
from backend.crm.schemas import CustomerSignal
from backend.crm.signals.base import signal

_OPEN_STATUSES = ("درحال بررسی", "درحال توسعه", "نمونه تأیید")


def calculate(con: duckdb.DuckDBPyConnection, customer_id: str,
              ref: dt.date, cfg: SignalConfig) -> CustomerSignal:
    rows = con.execute(
        "SELECT Status FROM dev_requests WHERE Customer_ID = ?",
        [customer_id],
    ).fetchall()
    open_requests = sum(1 for (s,) in rows if s in _OPEN_STATUSES)
    if open_requests == 0:
        return signal("dev_request", customer_id, status="neutral",
                      confidence=0.0, sample_size=len(rows),
                      evidence={"open_requests": 0},
                      reasons=[])
    return signal(
        "dev_request", customer_id, status="positive",
        confidence=min(1.0, open_requests / 2.0), sample_size=len(rows),
        evidence={"open_requests": open_requests, "total_requests": len(rows)},
        reasons=[f"{open_requests} open development request(s)"],
    )
