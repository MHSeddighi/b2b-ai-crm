"""A slow tool must degrade one signal, never stall the whole answer.

Before these bounds existed, a single CRM tool that never returned held the
SSE stream open until the browser's own 240s cap fired, so the user lost the
entire answer — including everything already gathered — and just saw
"connection lost". These tests pin the bounded behaviour.
"""
import asyncio

import pytest

from backend.agents import db_agent


class _HangingSession:
    """MCP session whose tool calls never return."""

    def __init__(self):
        self.calls = 0

    async def call_tool(self, name, arguments=None):
        self.calls += 1
        await asyncio.sleep(3600)


class _SlowForOne:
    """Returns promptly for everyone except one customer, who hangs."""

    def __init__(self, slow_id):
        self.slow_id = slow_id

    async def call_tool(self, name, arguments=None):
        if (arguments or {}).get("customer_id") == self.slow_id:
            await asyncio.sleep(3600)

        class _R:
            content = [type("T", (), {"text": '{"ok": true}'})()]
        return _R()


@pytest.mark.asyncio
async def test_hung_crm_tool_times_out_instead_of_hanging():
    session = _HangingSession()
    with pytest.raises((asyncio.TimeoutError, TimeoutError)):
        await db_agent._call_crm_tool(
            session, "get_customer_action_plan", {"customer_id": "C_1"},
            None, timeout=0.05,
        )
    assert session.calls == 1


@pytest.mark.asyncio
async def test_chaining_survives_one_hung_customer():
    """The healthy customers' plans still land; the hung one is dropped."""
    crm_results = {
        "top_at_risk_customers:3": {
            "columns": ["Customer_ID"],
            "rows": [["C_ok1"], ["C_slow"], ["C_ok2"]],
        }
    }
    session = _SlowForOne("C_slow")

    async def fake_ensure():
        return session

    # Per-call bound is what lets the gather finish while one call is stuck.
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(db_agent, "_ensure_mcp", fake_ensure)
        mp.setattr(db_agent, "CRM_TOOL_TIMEOUT_S", 0.05)
        chained = await asyncio.wait_for(
            db_agent._auto_chain_action_plans(crm_results, None), timeout=10
        )

    assert "C_slow" not in chained
    assert "action_plan:C_ok1" in crm_results
    assert "action_plan:C_ok2" in crm_results


@pytest.mark.asyncio
async def test_chaining_respects_an_already_expired_deadline():
    """With no budget left, chaining gives up rather than adding more delay."""
    crm_results = {
        "top_at_risk_customers:1": {"columns": ["Customer_ID"], "rows": [["C_slow"]]}
    }
    session = _HangingSession()

    async def fake_ensure():
        return session

    spent = db_agent._Deadline()
    spent.seconds = 0  # nothing left

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(db_agent, "_ensure_mcp", fake_ensure)
        chained = await asyncio.wait_for(
            db_agent._auto_chain_action_plans(crm_results, None, spent), timeout=10
        )
    assert chained == []


@pytest.mark.asyncio
async def test_slow_sql_returns_an_error_result_not_a_hang():
    """A stuck query must surface as a normal error result the agent can
    report, not stall the stream."""
    async def never(*_a, **_k):
        await asyncio.sleep(3600)

    async def noop_restart():
        return None

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(db_agent, "_ensure_mcp", lambda: asyncio.sleep(0, result=object()))
        mp.setattr(db_agent, "_call_query", never)
        mp.setattr(db_agent, "_restart_mcp", noop_restart)
        mp.setattr(db_agent, "SQL_TIMEOUT_S", 0.05)
        data = await asyncio.wait_for(db_agent._run_sql("SELECT 1"), timeout=10)

    assert "error" in data
    assert "timed out" in data["error"]


def test_answer_budget_leaves_room_before_the_browser_aborts():
    """The server must give up early enough to still compose and stream a
    reply; the frontend aborts at 240s (frontend/src/lib/chat-api.ts)."""
    assert db_agent.ANSWER_BUDGET_S < 240
    assert db_agent.ANSWER_BUDGET_S - db_agent.SQL_TIMEOUT_S > 0


def test_deadline_reports_expiry():
    d = db_agent._Deadline()
    assert not d.expired and d.remaining > 0
    d.seconds = 0
    assert d.expired
