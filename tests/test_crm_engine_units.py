"""Unit tests for reason engine, eligibility evaluator, and plan routing."""
from backend.agents.contracts import CRM_TOOLS, Plan, plan_steps
from backend.crm.actions.definitions import ACTIONS
from backend.crm.actions.eligibility import is_eligible
from backend.crm.schemas import CustomerSignal, CustomerState, StateDimension
from backend.crm.state.reason_engine import build_reasons


def _sig(signal_id, status="neutral", confidence=1.0, evidence=None,
         reasons=None, direction="stable", sample_size=1):
    return CustomerSignal(signal_id=signal_id, customer_id="X", status=status,
                          confidence=confidence, evidence=evidence or {},
                          reasons=reasons or [], direction=direction,
                          sample_size=sample_size)


def _state(**dims):
    base = {k: StateDimension(status="unknown") for k in
            ("value", "churn_risk", "growth_opportunity",
             "relationship_health", "profitability", "payment_risk")}
    base.update(dims)
    return CustomerState(customer_id="X", **base)


class TestReasonEngine:
    def test_declining_purchase_reason(self):
        sigs = {"purchase_trend": _sig("purchase_trend", "warning", 0.8,
                                       evidence={"revenue_change_pct": -38})}
        reasons = build_reasons(sigs)
        types = {r.type for r in reasons}
        assert "PURCHASE_DECLINING" in types

    def test_no_signals_no_reasons(self):
        assert build_reasons({}) == []

    def test_reasons_carry_source_signal(self):
        sigs = {"payment_behavior": _sig("payment_behavior", "critical", 0.9)}
        reasons = build_reasons(sigs)
        assert any("payment_behavior" in r.source_signals for r in reasons)


class TestEligibility:
    def test_forbidden_overrides_eligible(self):
        # CROSS_SELL forbidden by unresolved complaint even though growth is high.
        cross = next(a for a in ACTIONS if a.action_id == "CROSS_SELL")
        signals = {
            "growth_potential": _sig("growth_potential", "positive", 1.0,
                                     evidence={"level": "high"}),
            "complaint_impact": _sig("complaint_impact", "critical", 1.0,
                                     evidence={"unresolved_count": 1}),
        }
        state = _state(churn_risk=StateDimension(status="low"),
                       relationship_health=StateDimension(status="healthy"))
        ok, blocked = is_eligible(cross, signals, state)
        assert ok is False
        assert blocked  # forbidden reason recorded

    def test_eligible_when_conditions_hold(self):
        cross = next(a for a in ACTIONS if a.action_id == "CROSS_SELL")
        signals = {
            "growth_potential": _sig("growth_potential", "positive", 1.0,
                                     evidence={"level": "high"}),
        }
        state = _state(churn_risk=StateDimension(status="low"),
                       relationship_health=StateDimension(status="healthy"))
        ok, _ = is_eligible(cross, signals, state)
        assert ok is True


class TestPlanRouting:
    def test_crm_tool_becomes_crm_step(self):
        plan = Plan(steps=[{"tool": "get_next_best_actions",
                            "input": {"customer_id": "C_1"}}])
        steps = plan_steps(plan, max_queries=3)
        assert steps == [{"kind": "crm", "tool": "get_next_best_actions",
                          "customer_id": "C_1", "purpose": ""}]

    def test_crm_tool_without_customer_dropped(self):
        plan = Plan(steps=[{"tool": "get_next_best_actions", "input": {}}])
        assert plan_steps(plan, max_queries=3) == []

    def test_all_tools_registered(self):
        assert CRM_TOOLS == {
            "get_customer_signals", "get_customer_state",
            "get_customer_reasons", "get_next_best_actions",
            "get_customer_action_plan", "top_at_risk_customers",
        }
