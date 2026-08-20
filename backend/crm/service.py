"""CustomerIntelligenceService — assembles the canonical customer-intelligence
object and exposes the five tool-level accessors consumed by the chatbot."""
from __future__ import annotations

import datetime as dt
from typing import Any

from backend.crm import data
from backend.crm.actions.next_best_action import recommend
from backend.crm.engine import SignalEngine
from backend.crm.schemas import (
    CustomerIntelligence,
    CustomerSignal,
    CustomerState,
    DataQuality,
    Reason,
    RecommendedAction,
)
from backend.crm.state import build_reasons, build_state


class CustomerIntelligenceService:
    def __init__(self, engine: SignalEngine | None = None) -> None:
        self.engine = engine or SignalEngine()

    # ------------------------------------------------------------------ core
    def get_intelligence(self, customer_id: str) -> CustomerIntelligence:
        con = data.connect()
        try:
            if not data.customer_exists(con, customer_id):
                return CustomerIntelligence(customer_id=customer_id)
            ref = data.reference_date(con)
            signals = self.engine.calculate(con, customer_id, ref)
        finally:
            con.close()

        state = build_state(customer_id, signals)
        reasons = build_reasons(signals)
        quality = self._data_quality(signals)
        actions = recommend(signals, state, quality.overall)

        return CustomerIntelligence(
            customer_id=customer_id,
            signals=signals,
            state=state,
            reasons=reasons,
            next_best_actions=actions,
            data_quality=quality,
        )

    # ------------------------------------------------------------ tool access
    def get_signals(self, customer_id: str) -> dict[str, CustomerSignal]:
        return self.get_intelligence(customer_id).signals

    def get_state(self, customer_id: str) -> CustomerState:
        return self.get_intelligence(customer_id).state

    def get_reasons(self, customer_id: str) -> list[Reason]:
        return self.get_intelligence(customer_id).reasons

    def get_next_best_actions(self, customer_id: str) -> list[RecommendedAction]:
        return self.get_intelligence(customer_id).next_best_actions

    def get_action_plan(self, customer_id: str) -> dict[str, Any]:
        ci = self.get_intelligence(customer_id)
        return {
            "customer_id": customer_id,
            "state": ci.state.model_dump() if ci.state else None,
            "reasons": [r.model_dump() for r in ci.reasons],
            "next_best_actions": [a.model_dump() for a in ci.next_best_actions],
            "data_quality": ci.data_quality.model_dump(),
            "calculated_at": ci.calculated_at.isoformat(),
        }

    # --------------------------------------------------------- data quality
    def _data_quality(self, signals: dict[str, CustomerSignal]) -> DataQuality:
        warnings: list[str] = []
        confs = [s.confidence for s in signals.values() if s is not None]

        profit = signals.get("profit")
        if profit is not None and profit.evidence.get("cost_coverage") is not None:
            cov = profit.evidence["cost_coverage"]
            if cov < 1.0:
                warnings.append(f"Cost data covers only {cov:.0%} of revenue")

        sow = signals.get("share_of_wallet")
        if sow is not None and sow.evidence.get("stale_days") is not None:
            if sow.evidence["stale_days"] > 365:
                warnings.append("Wallet-share estimate is stale (>1 year old)")

        if any(s is not None and s.confidence < 0.3 and s.sample_size > 0
               for s in signals.values()):
            warnings.append("Some signals are low-confidence (small sample)")

        overall = round(sum(confs) / len(confs), 3) if confs else 0.0
        return DataQuality(overall=overall, warnings=warnings)


service = CustomerIntelligenceService()
