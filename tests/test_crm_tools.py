"""MCP tool layer tests: the five chatbot-facing CRM tools."""
import json

from backend.crm import tools


class TestCrmTools:
    def test_signals_tool_returns_all_signals(self):
        data = json.loads(tools.get_customer_signals("C_010649"))
        assert "profit" in data and "churn_risk" in data

    def test_state_tool_returns_dimensions(self):
        data = json.loads(tools.get_customer_state("C_010649"))
        assert "value" in data and "churn_risk" in data and "payment_risk" in data

    def test_reasons_tool_is_a_list(self):
        data = json.loads(tools.get_customer_reasons("C_010649"))
        assert isinstance(data, list)

    def test_actions_tool_is_ranked_list(self):
        data = json.loads(tools.get_next_best_actions("C_010649"))
        assert isinstance(data, list)
        assert len(data) <= 3
        for a in data:
            assert "action_id" in a and "priority" in a

    def test_action_plan_tool_has_expected_keys(self):
        data = json.loads(tools.get_customer_action_plan("C_010649"))
        assert {"customer_id", "state", "reasons", "next_best_actions",
                "data_quality", "calculated_at"} <= set(data.keys())

    def test_unknown_customer_signals_empty(self):
        data = json.loads(tools.get_customer_signals("NOPE"))
        assert data == {}
