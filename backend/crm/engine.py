"""Signal engine: compute every signal for a customer in one pass.

Opens a single read-only DuckDB connection and reuses it across all base
signals (so a customer is not re-queried N times), then computes the derived
signals that consume the base results.
"""
from __future__ import annotations

import datetime as dt

import duckdb

from backend.crm import data
from backend.crm.config import SIGNAL_CONFIG, SignalConfig
from backend.crm.schemas import CustomerSignal
from backend.crm.signals import BASE_SIGNALS, DERIVED_SIGNALS


class SignalEngine:
    def __init__(self, cfg: SignalConfig | None = None) -> None:
        self.cfg = cfg or SIGNAL_CONFIG

    def calculate(self, con: duckdb.DuckDBPyConnection, customer_id: str,
                  ref: dt.date | None = None) -> dict[str, CustomerSignal]:
        if ref is None:
            ref = data.reference_date(con)

        signals: dict[str, CustomerSignal] = {}
        for signal_id, fn in BASE_SIGNALS.items():
            signals[signal_id] = fn(con, customer_id, ref, self.cfg)

        for signal_id, fn in DERIVED_SIGNALS.items():
            signals[signal_id] = fn(customer_id, signals, ref, self.cfg)

        return signals

    def calculate_for(self, customer_id: str) -> dict[str, CustomerSignal]:
        """Convenience wrapper that owns the connection lifecycle."""
        con = data.connect()
        try:
            if not data.customer_exists(con, customer_id):
                return {}
            return self.calculate(con, customer_id)
        finally:
            con.close()
