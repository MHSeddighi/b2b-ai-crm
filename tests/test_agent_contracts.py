"""Tests for the structured JSON contracts and the simplified agent pipeline.

Covers: strict JSON parsing (no regex), the single-plan + single-compose flow,
minimal LLM/MCP call counts, explicit failures (no silent fallback).
"""
import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest

from backend.agents import contracts, db_agent
from backend.agents.contracts import (
    Plan,
    parse_blocks_json,
    parse_plan,
)


def _run_async(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# ---------------------------------------------------------------------------
# Contracts
# ---------------------------------------------------------------------------
def test_parse_plan_strips_code_fences_and_steps():
    text = ('```json\n{"intent":"x","assumption":"a",'
            '"steps":[{"tool":"query","input":{"query":"SELECT 1","purpose":"p"}}]}\n```')
    plan = parse_plan(text)
    assert plan.intent == "x"
    assert plan.assumption == "a"
    assert len(plan.steps) == 1
    assert plan.steps[0].tool == "query"
    assert plan.steps[0].input["query"] == "SELECT 1"


def test_parse_plan_tolerates_queries_alias():
    plan = parse_plan('{"assumption":"a","queries":[{"sql":"SELECT 1"}]}')
    assert len(plan.items) == 1
    assert plan.items[0].sql == "SELECT 1"


def test_plan_steps_flattens_query_and_reuse():
    from backend.agents.contracts import PlanStep

    plan = Plan(steps=[
        PlanStep(tool="query", input={"query": "SELECT 1", "purpose": "a"}),
        PlanStep(tool="reuse", input={"resultId": "r_old", "purpose": "reuse"}),
        PlanStep(tool="query", input={"query": "SELECT 2", "purpose": "b"}),
    ])
    steps = contracts.plan_steps(plan, max_queries=1)
    queries = [s for s in steps if s["kind"] == "query"]
    assert len(queries) == 1
    assert queries[0]["sql"] == "SELECT 1"
    # reuse is never capped
    assert any(s["kind"] == "reuse" and s["resultId"] == "r_old" for s in steps)


def test_parse_blocks_json_array_and_wrapper():
    arr = parse_blocks_json('[{"id":"b1","type":"markdown","content":"x"}]')
    assert arr and arr[0]["type"] == "markdown"
    wrapped = parse_blocks_json('{"blocks":[{"id":"b1","type":"markdown","content":"x"}]}')
    assert wrapped and wrapped[0]["type"] == "markdown"
    # non-JSON prose -> None
    assert parse_blocks_json("just some prose answer") is None


# ---------------------------------------------------------------------------
# Minimal call counts: one plan + one compose, one SQL query
# ---------------------------------------------------------------------------
class _FakeSession:
    async def initialize(self):
        return None

    async def call_tool(self, name, arguments=None):
        raise AssertionError("call_tool should be bypassed (run_sql patched)")


class _CountingLLM:
    """Side-effect router for _llm_call that counts calls.

    The planner is called with PLANNER_SYSTEM and the composer with
    COMPOSER_SYSTEM; we distinguish by the system prompt argument.
    """

    def __init__(self):
        self.calls = []
        self.plan_json = ('{"intent":"cnt","assumption":"a",'
                          '"steps":[{"tool":"query","input":{"query":"SELECT 1","purpose":"count"}}]}')
        self.blocks_json = '{"blocks":[{"id":"b1","type":"markdown","content":"ok"}]}'

    def __call__(self, system, user, temperature=0.0):
        self.calls.append(system)
        if system == db_agent.PLANNER_SYSTEM:
            return self.plan_json
        return self.blocks_json


@pytest.mark.asyncio
async def test_database_answer_uses_two_llm_calls_and_one_query():
    llm = _CountingLLM()
    run_calls = []

    async def fake_run_sql(sql):
        run_calls.append(sql)
        return {"resultId": "server_1", "columns": ["n"], "rows": [[644]], "n_rows": 1}

    with patch.object(db_agent, "_llm_call", side_effect=llm), \
         patch.object(db_agent, "_run_sql", side_effect=fake_run_sql):
        result = await db_agent._database_answer("چند مشتری؟", db_agent.SessionState("t"))

    assert len(llm.calls) == 2  # plan + compose (no extra retries/conversational)
    assert run_calls == ["SELECT 1"]
    assert result["blocks"], "must produce blocks"
    assert "server_1" in result["results"]


@pytest.mark.asyncio
async def test_query_sql_error_is_explicit():
    """When a query returns an error, surface it explicitly (no silent fallback)."""
    with patch.object(db_agent, "_llm_call",
                      new=Mock(return_value=('{"action":"query","sql":"SELECT bad","purpose":"x"}'))), \
         patch.object(db_agent, "_fix_sql", new=AsyncMock(return_value=None)), \
         patch.object(db_agent, "_run_sql",
                      new=AsyncMock(return_value={"error": "syntax error"})):
        result = await db_agent._database_answer("سؤال", db_agent.SessionState("t"))

    assert result["blocks"][0].type == "markdown"
    assert "error" in result or "خطا" in result["blocks"][0].content


@pytest.mark.asyncio
async def test_sql_self_corrects_once_and_retries():
    """A failing SQL query is fixed once by the LLM and re-run; only then does
    an error surface if the fix still fails."""
    run_sql_calls = []

    async def fake_run_sql(sql):
        run_sql_calls.append(sql)
        if sql.startswith("SELECT bad"):
            return {"error": "syntax error near asof"}
        return {"resultId": "r1", "columns": ["n"], "rows": [[10]], "n_rows": 1}

    with patch.object(db_agent, "_llm_call",
                      new=Mock(return_value=('{"intent":"x","assumption":"",'
                                             '"steps":[{"tool":"query","input":{"query":"SELECT bad","purpose":"p"}}]}'))), \
         patch.object(db_agent, "_fix_sql",
                      new=AsyncMock(return_value="SELECT 1 AS n")), \
         patch.object(db_agent, "_run_sql", side_effect=fake_run_sql):
        result = await db_agent._database_answer("سؤال", db_agent.SessionState("t"))

    assert run_sql_calls == ["SELECT bad", "SELECT 1 AS n"]
    assert result["results"]["r1"].rows == [[10]]


@pytest.mark.asyncio
async def test_plan_failure_is_explicit():
    with patch.object(db_agent, "_plan", new=Mock(side_effect=RuntimeError("llm down"))):
        result = await db_agent._database_answer("سؤال", db_agent.SessionState("t"))
    assert result["blocks"][0].type == "markdown"
    assert "error" in result


@pytest.mark.asyncio
async def test_reuse_action_uses_existing_result():
    ctx = db_agent.SessionState("t")
    ctx.add_result("r_old", "count", ["n"], [[644]], 1)
    with patch.object(db_agent, "_llm_call",
                      new=Mock(return_value=('{"intent":"follow_up","assumption":"",'
                                             '"steps":[{"tool":"reuse","input":{"resultId":"r_old"}}]}'))):
        result = await db_agent._database_answer("چند مشتری؟", ctx)
    assert result["blocks"], "must produce blocks"
    assert "r_old" in result["results"]
    assert result["results"]["r_old"].rows == [[644]]


@pytest.mark.asyncio
async def test_run_sql_restarts_mcp_and_retries_once_on_dead_session():
    """A dead MCP session is restarted and the query retried exactly once."""
    sqls = []

    async def fake_call(session, sql):
        sqls.append(sql)
        if len(sqls) == 1:
            raise ConnectionError("MCP session died")
        return {"resultId": "r1", "columns": ["n"], "rows": [[1]], "n_rows": 1}

    with patch.object(db_agent, "_ensure_mcp", new=AsyncMock(return_value="fresh-session")), \
         patch.object(db_agent, "_restart_mcp", new=AsyncMock()) as restart, \
         patch.object(db_agent, "_call_query", side_effect=fake_call):
        out = await db_agent._run_sql("SELECT 1")

    assert out["resultId"] == "r1"
    assert sqls == ["SELECT 1", "SELECT 1"]
    restart.assert_awaited_once()
