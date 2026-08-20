"""Integration tests for the agent's block flow (using a fake MCP session).

We monkeypatch _llm_call / _run_sql to avoid real network/DB calls, and
verify the agent produces ordered blocks, references resultIds, and handles
huge results.
"""
from unittest.mock import AsyncMock, Mock, patch

import json

import pytest

from backend.agents import db_agent


def _query_plan(sql="SELECT 1", assumption="", intent="x"):
    return ('{"intent":"%s","assumption":"%s",'
            '"steps":[{"tool":"query","input":{"query":"%s","purpose":"p"}}]}'
            % (intent, assumption, sql))


def _chat_plan():
    return '{"intent":"chat","assumption":"","steps":[]}'


class FakeSession:
    async def initialize(self):
        return None

    async def call_tool(self, name, arguments=None):
        raise AssertionError("call_tool should be bypassed (run_sql patched)")


@pytest.mark.asyncio
async def test_database_answer_returns_ordered_blocks_with_result_ids():
    blocks_raw = [
        {"id": "b1", "type": "markdown", "content": "intro"},
        {"id": "b2", "type": "chart", "resultId": "r1", "chartType": "line", "xKey": "month", "series": [{"dataKey": "sales"}]},
    ]
    with patch.object(db_agent, "_llm_call",
                      new=Mock(return_value=_query_plan("SELECT 1", assumption="assumption text"))), \
         patch.object(db_agent, "_run_sql", new=AsyncMock(return_value={
             "resultId": "r1", "columns": ["month", "sales"], "rows": [["m1", 10]], "n_rows": 1,
         })), \
         patch.object(db_agent, "_compose", new=AsyncMock(return_value=blocks_raw)):
        result = await db_agent._database_answer("sales trend?", db_agent.SessionState("t"))

    assert [b.type for b in result["blocks"]] == ["markdown", "chart"]
    assert result["results"]["r1"].rows == [["m1", 10]]


@pytest.mark.asyncio
async def test_huge_result_still_composes_answer():
    """A huge result no longer blocks composition and asks the user how to
    proceed — the MCP server already returns a representative random sample,
    so the agent composes a normal summary from it instead."""
    blocks_raw = [{"id": "b1", "type": "markdown", "content": "خلاصه"}]
    session_state = db_agent.SessionState("t")
    with patch.object(db_agent, "_llm_call", new=Mock(return_value=_query_plan("SELECT * FROM sales"))), \
         patch.object(db_agent, "_run_sql", new=AsyncMock(return_value={
             "resultId": "r1", "columns": ["x"], "rows": [], "n_rows": 5000,
         })), \
         patch.object(db_agent, "_compose", new=AsyncMock(return_value=blocks_raw)):
        # Go through answer() (not _database_answer directly): turn-recording
        # is centralized there now so it happens for every outcome, not just
        # the success path.
        result = await db_agent.answer("all sales?", session_state=session_state)

    assert result["blocks"][0].type == "markdown"
    assert result["blocks"][0].content == "خلاصه"
    assert result["results"]["r1"].n_rows == 5000
    # the turn must still be recorded so a follow-up question keeps context
    assert session_state.log


@pytest.mark.asyncio
async def test_chat_action_returns_conversational_answer():
    with patch.object(db_agent, "_llm_call",
                      new=Mock(side_effect=[
                          _chat_plan(),
                          "سلام! چطور می‌توانم کمک کنم؟",
                      ])):
        result = await db_agent._database_answer("hello", db_agent.SessionState("t"))
    assert result["blocks"][0].type == "markdown"
    assert not result["results"]


@pytest.mark.asyncio
async def test_compose_failure_is_explicit():
    """A compose failure surfaces an explicit markdown block (no silent fallback)."""
    with patch.object(db_agent, "_llm_call", new=Mock(return_value=_query_plan("SELECT 1", assumption="top customer"))), \
         patch.object(db_agent, "_run_sql", new=AsyncMock(return_value={
             "resultId": "r1", "columns": ["month", "sales"], "rows": [["m1", 10], ["m2", 20]], "n_rows": 2,
         })), \
         patch.object(db_agent, "_compose", new=AsyncMock(side_effect=RuntimeError("llm down"))):
        result = await db_agent._database_answer("trend?", db_agent.SessionState("t"))

    assert result["blocks"], "must never be empty"
    assert result["blocks"][0].type == "markdown"
    assert "error" in result  # explicit failure surfaced


@pytest.mark.asyncio
async def test_assumption_flows_into_compose():
    captured = {}

    async def fake_compose(question, ctx, results, assumption, crm_results=None, trace=None):
        captured["assumption"] = assumption
        return [{"id": "b1", "type": "markdown", "content": "ok"}]

    with patch.object(db_agent, "_llm_call", new=Mock(return_value=_query_plan("SELECT 1", assumption="picked C_937594"))), \
         patch.object(db_agent, "_run_sql", new=AsyncMock(return_value={
             "resultId": "r1", "columns": ["x"], "rows": [[1]], "n_rows": 1,
         })), \
         patch.object(db_agent, "_compose", new=fake_compose):
        await db_agent._database_answer("one customer?", db_agent.SessionState("t"))
    assert captured.get("assumption") == "picked C_937594"


@pytest.mark.asyncio
async def test_compose_blocks_builds_inline_table_from_crm_only_answer():
    """A CRM-only answer (e.g. the at-risk list) must still produce table
    blocks even though there are no SQL resultIds to reference."""
    crm_results = {
        "top_at_risk_customers:10": {
            "columns": ["Customer_ID", "complaints", "orders", "bounced", "risk_score"],
            "rows": [
                ["C_117580", 9, 622, 3, 92],
                ["C_683666", 37, 44, 2, 92],
            ],
            "n_rows": 2,
        }
    }
    blocks_raw = [
        {"id": "t1", "type": "table", "columns": ["Customer_ID", "complaints", "orders", "bounced", "risk_score"],
         "rows": [["C_117580", 9, 622, 3, 92], ["C_683666", 37, 44, 2, 92]],
         "title": "مشتریان در معرض ریسک"},
    ]
    with patch.object(db_agent, "_llm_call_async",
                      new=AsyncMock(return_value=json.dumps(blocks_raw))):
        blocks = await db_agent._compose_blocks(
            "کدام مشتری‌ها در معرض از دست رفتن هستند؟",
            db_agent.SessionState("t"),
            results={},
            assumption="",
            crm_results=crm_results,
            trace=None,
        )
    tables = [b for b in blocks if b.get("type") == "table"]
    assert tables, "CRM-only answers must produce table blocks"
    assert tables[0]["rows"][0][0] == "C_117580"
    assert tables[0]["columns"] == ["Customer_ID", "complaints", "orders", "bounced", "risk_score"]


@pytest.mark.asyncio
async def test_compose_blocks_returns_empty_without_any_data():
    """No results and no CRM data -> no blocks (conversational only)."""
    with patch.object(db_agent, "_llm_call_async",
                      new=AsyncMock(return_value="[]")):
        blocks = await db_agent._compose_blocks(
            "سلام", db_agent.SessionState("t"),
            results={}, assumption="", crm_results=None, trace=None,
        )
    assert blocks == []


class _TextContent:
    def __init__(self, text):
        self.text = text


class _TextResult:
    def __init__(self, text):
        self.content = [_TextContent(text)]


@pytest.mark.asyncio
async def test_at_risk_question_auto_chains_action_plans():
    """A top_at_risk_customers question must deterministically chain
    get_customer_action_plan for every returned customer (engine-driven
    recommendations, not LLM-remembered)."""

    class ChainSession:
        def __init__(self):
            self.calls = []

        async def initialize(self):
            return None

        async def call_tool(self, name, arguments=None):
            self.calls.append((name, arguments or {}))
            if name == "top_at_risk_customers":
                return _TextResult(json.dumps({
                    "columns": ["Customer_ID", "complaints", "orders", "bounced", "risk_score"],
                    "rows": [["C_117580", 9, 622, 3, 92], ["C_683666", 37, 44, 2, 92]],
                    "n_rows": 2,
                }))
            if name == "get_customer_action_plan":
                return _TextResult(json.dumps({
                    "customer_id": (arguments or {}).get("customer_id"),
                    "state": {"churn_risk": {"status": "critical"}},
                    "reasons": [],
                    "next_best_actions": [
                        {"action_id": "RETENTION_CALL", "name": "Retention call",
                         "priority": 0.9, "reason": "at risk",
                         "suggested_next_step": "call the customer"},
                    ],
                    "data_quality": {"overall": 0.9},
                    "calculated_at": "2024-01-01T00:00:00",
                }))
            raise AssertionError(f"unexpected tool {name}")

    plan = ('{"intent":"at_risk","assumption":"","steps":['
            '{"tool":"top_at_risk_customers","input":{"limit":10}}]}')
    session = ChainSession()
    seen: dict = {}

    async def fake_compose(question, ctx, results, assumption, crm_results=None, trace=None):
        seen["crm"] = dict(crm_results or {})
        return [{"id": "b1", "type": "markdown", "content": "ok"}]

    with patch.object(db_agent, "_llm_call_async", new=AsyncMock(return_value=plan)), \
         patch.object(db_agent, "_ensure_mcp", new=AsyncMock(return_value=session)), \
         patch.object(db_agent, "_compose", new=fake_compose):
        await db_agent._database_answer("at risk?", db_agent.SessionState("t"))

    tools = [c[0] for c in session.calls]
    assert tools == ["top_at_risk_customers",
                     "get_customer_action_plan", "get_customer_action_plan"]
    assert "action_plan:C_117580" in seen["crm"]
    assert "action_plan:C_683666" in seen["crm"]
    # the engine-computed actions are passed to the composer
    assert seen["crm"]["action_plan:C_117580"]["next_best_actions"][0]["action_id"] == "RETENTION_CALL"


@pytest.mark.asyncio
async def test_action_plan_not_fetched_twice_when_plan_has_direct_step():
    """If the LLM plan already contains a get_customer_action_plan step for a
    customer, the auto-chainer must NOT call it again (exactly one MCP call)."""

    class DedupSession:
        def __init__(self):
            self.calls = []

        async def initialize(self):
            return None

        async def call_tool(self, name, arguments=None):
            self.calls.append((name, arguments or {}))
            if name == "top_at_risk_customers":
                return _TextResult(json.dumps({
                    "columns": ["Customer_ID", "complaints", "orders", "bounced", "risk_score"],
                    "rows": [["C_117580", 9, 622, 3, 92]],
                    "n_rows": 1,
                }))
            if name == "get_customer_action_plan":
                return _TextResult(json.dumps({
                    "customer_id": (arguments or {}).get("customer_id"),
                    "state": {"churn_risk": {"status": "critical"}},
                    "reasons": [],
                    "next_best_actions": [{"action_id": "RETENTION_CALL"}],
                    "data_quality": {"overall": 0.9},
                    "calculated_at": "2024-01-01T00:00:00",
                }))
            raise AssertionError(f"unexpected tool {name}")

    # Plan calls top_at_risk_customers AND a direct action plan step for C_117580.
    plan = ('{"intent":"at_risk","assumption":"","steps":['
            '{"tool":"top_at_risk_customers","input":{"limit":10}},'
            '{"tool":"get_customer_action_plan","input":{"customer_id":"C_117580"}}]}')
    session = DedupSession()
    seen: dict = {}

    async def fake_compose(question, ctx, results, assumption, crm_results=None, trace=None):
        seen["crm"] = dict(crm_results or {})
        return [{"id": "b1", "type": "markdown", "content": "ok"}]

    with patch.object(db_agent, "_llm_call_async", new=AsyncMock(return_value=plan)), \
         patch.object(db_agent, "_ensure_mcp", new=AsyncMock(return_value=session)), \
         patch.object(db_agent, "_compose", new=fake_compose):
        await db_agent._database_answer("at risk?", db_agent.SessionState("t"))

    action_calls = [c for c in session.calls if c[0] == "get_customer_action_plan"]
    assert len(action_calls) == 1, f"expected exactly ONE action plan call, got {len(action_calls)}"
    assert seen["crm"].get("action_plan:C_117580"), "action_plan key missing for the customer"
