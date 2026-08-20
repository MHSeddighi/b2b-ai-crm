"""Tests that the agent answers business questions with ONE MCP query,
using the static Customer360 schema in context (no per-question discovery).
"""
import json
from unittest.mock import AsyncMock, Mock, patch

import pytest

from backend.agents import db_agent


class _TextContent:
    def __init__(self, text):
        self.text = text


class _TextResult:
    def __init__(self, text):
        self.content = [_TextContent(text)]


class RecordingSession:
    """Fake MCP session that records every tool call."""

    def __init__(self, run_response=None):
        self.calls: list[tuple[str, dict]] = []
        self._run_response = run_response or {
            "resultId": "r1", "columns": ["n"], "rows": [[644]], "n_rows": 1,
        }

    async def initialize(self):
        return None

    async def call_tool(self, name, arguments=None):
        arguments = arguments or {}
        self.calls.append((name, arguments))
        if name in ("query", "run_sql"):
            return _TextResult(json.dumps(self._run_response))
        if name == "get_schema":
            return _TextResult(json.dumps({"tables": [{"name": "customers"}]}))
        if name == "list_tables":
            return _TextResult(json.dumps([{"table": "customers", "rows": 644}]))
        raise AssertionError(f"unexpected tool {name}")


def _query_plan(sql="SELECT 1", purpose="p"):
    return '{"intent":"x","assumption":"","steps":[{"tool":"query","input":{"query":"%s","purpose":"%s"}}]}' % (sql, purpose)


@pytest.mark.asyncio
async def test_business_question_answered_with_single_query_call():
    """A common question needs exactly ONE analytical MCP call, no discovery."""
    session = RecordingSession()
    with patch.object(db_agent, "_llm_call",
                      new=Mock(return_value=_query_plan("SELECT count(DISTINCT Customer_ID) AS n FROM sales"))), \
         patch.object(db_agent, "_ensure_mcp", new=AsyncMock(return_value=session)), \
         patch.object(db_agent, "_run_sql", wraps=db_agent._run_sql):
        result = await db_agent._database_answer("how many customers?", db_agent.SessionState("t"))

    tool_names = [name for name, _ in session.calls]
    assert tool_names.count("query") + tool_names.count("run_sql") == 1, tool_names
    assert "get_schema" not in tool_names
    assert "list_tables" not in tool_names
    assert result["results"]["r1"].rows == [[644]]


@pytest.mark.asyncio
async def test_agent_uses_static_schema_not_discovery():
    """The agent must not call get_schema/list_tables for a normal question."""
    session = RecordingSession()
    with patch.object(db_agent, "_llm_call", new=Mock(return_value=_query_plan())), \
         patch.object(db_agent, "_ensure_mcp", new=AsyncMock(return_value=session)):
        await db_agent._database_answer("total revenue?", db_agent.SessionState("t"))

    names = [n for n, _ in session.calls]
    assert "get_schema" not in names
    assert "list_tables" not in names


@pytest.mark.asyncio
async def test_result_id_comes_from_server_not_llm():
    """resultId in the response must come from the MCP server, not the LLM."""
    session = RecordingSession(run_response={
        "resultId": "server-gen-1", "columns": ["n"], "rows": [[10]], "n_rows": 1,
    })
    with patch.object(db_agent, "_llm_call", new=Mock(return_value=_query_plan())), \
         patch.object(db_agent, "_ensure_mcp", new=AsyncMock(return_value=session)):
        result = await db_agent._database_answer("how many?", db_agent.SessionState("t"))
    assert "server-gen-1" in result["results"]
    assert "llm-wanted-id" not in result["results"]


@pytest.mark.asyncio
async def test_failed_query_is_explicit_not_retried():
    """A DB error surfaces explicitly (no silent retry/fallback)."""
    async def fake_run_sql(sql):
        return {"error": "to_char does not exist"}

    with patch.object(db_agent, "_llm_call", new=Mock(return_value=_query_plan("SELECT to_char(1) AS m"))), \
         patch.object(db_agent, "_fix_sql", new=AsyncMock(return_value=None)), \
         patch.object(db_agent, "_run_sql", side_effect=fake_run_sql):
        result = await db_agent._database_answer("trend?", db_agent.SessionState("t"))

    assert result["blocks"][0].type == "markdown"
    assert "error" in result or "خطا" in result["blocks"][0].content


@pytest.mark.asyncio
async def test_huge_result_not_sent_to_compose():
    """A huge result triggers the huge guard before any block composition."""
    session = RecordingSession(run_response={
        "resultId": "r_big", "columns": ["x"], "rows": [], "n_rows": 5000,
    })
    with patch.object(db_agent, "_llm_call", new=Mock(return_value=_query_plan("SELECT * FROM sales"))), \
         patch.object(db_agent, "_ensure_mcp", new=AsyncMock(return_value=session)):
        result = await db_agent._database_answer("all rows?", db_agent.SessionState("t"))
    assert "5,000" in result["blocks"][0].content
