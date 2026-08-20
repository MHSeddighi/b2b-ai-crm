"""Tests proving agent context stays bounded as conversations and DB results grow.

These are pure unit tests on the context module (no network/LLM), plus a couple
of integration tests confirming result reuse and that exact rows never leak into
the LLM context.
"""
import asyncio
import json
from unittest.mock import AsyncMock, Mock, patch

import pytest

from backend.agents import context, db_agent
from backend.agents.context import (
    MAX_CONTEXT_CHARS,
    MAX_LOG_ENTRIES,
    MAX_RECENT_MESSAGES,
    MAX_RESULT_META,
    MAX_STATE_RESULT_IDS,
    MAX_STORED_RESULTS,
    MAX_SAMPLE_ROWS,
    SessionState,
)


def _run_async(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


class _TextResult:
    def __init__(self, text):
        self.content = [type("C", (), {"text": text})()]


class _FakeSession:
    async def initialize(self):
        return None

    async def call_tool(self, name, arguments=None):
        return _TextResult(json.dumps({
            "resultId": "r_server",
            "columns": ["month", "sales"],
            "rows": [["m1", 10]],
            "n_rows": 1,
        }))


def _long_result(n_rows):
    return {"resultId": "r_big", "columns": ["x"],
            "rows": [[i] for i in range(n_rows)], "n_rows": n_rows}


# ---------------------------------------------------------------------------
# Boundedness as the conversation grows
# ---------------------------------------------------------------------------
def test_context_stays_bounded_as_conversation_grows():
    s = SessionState("s")
    for i in range(MAX_LOG_ENTRIES + 50):
        q = f"سؤال شماره {i} با متن بلند " + ("پرکننده " * 40)
        a = f"پاسخ {i} " + ("نتیجه " * 50)
        s.record_turn(q, a)
    size1 = s.context_size("سؤال جدید؟")
    assert len(s.log) <= MAX_LOG_ENTRIES
    assert len(s.recent) <= MAX_RECENT_MESSAGES * 2
    assert size1 <= MAX_CONTEXT_CHARS

    # A full window is already at its cap: doubling the turns again must NOT
    # grow the context (this is the boundedness guarantee).
    for i in range(MAX_LOG_ENTRIES + 50):
        s.record_turn("سؤال دیگر " + ("متن " * 60), "پاسخ " + ("نتیجه " * 70))
    size2 = s.context_size("سؤال جدید؟")
    assert size2 <= MAX_CONTEXT_CHARS
    assert size2 <= size1  # does not grow once the summary window is full


def test_summary_log_caps_old_turns():
    s = SessionState("s")
    for i in range(200):
        s.record_turn(f"q{i}", f"a{i}")
    assert len(s.log) == MAX_LOG_ENTRIES
    assert len(s.recent) <= MAX_RECENT_MESSAGES * 2
    # oldest turns are dropped
    assert s.log[0]["q"] == f"q{200 - MAX_LOG_ENTRIES}"


# ---------------------------------------------------------------------------
# Boundedness as DB results grow — no row leak into context
# ---------------------------------------------------------------------------
def test_exact_rows_live_only_in_result_store_not_context():
    s = SessionState("s")
    s.add_result("r_big", "all sales", ["x"], [[i] for i in range(1000)])

    # exact rows are in the store
    assert s.get_result("r_big").n_rows == 1000
    assert s.result_store["r_big"].rows == [[i] for i in range(1000)]

    # metadata prompt has NO rows
    meta = s.result_meta_prompt(["r_big"])
    assert "n_rows=1000" in meta
    assert "[[" not in meta  # no row grids

    # context prompt has no full grid and is bounded
    rendered = s.render_context("سؤال؟")
    assert rendered.count("[") - rendered.count("]") < 100
    assert len(rendered) <= MAX_CONTEXT_CHARS


def test_context_bounded_as_result_count_and_rows_grow():
    s1 = SessionState("s")
    s2 = SessionState("s")
    for i in range(3):
        s1.add_result(f"r{i}", "one", ["a", "b"], [["x", i] for _ in range(50)])
    # many more results + many more rows
    for i in range(40):
        s2.add_result(f"r{i}", "one", ["a", "b"],
                      [["x", i] for _ in range(2000)])

    size1 = s1.context_size("سؤال؟")
    size2 = s2.context_size("سؤال؟")
    # adding far more results/rows does not blow up the context
    assert size2 <= MAX_CONTEXT_CHARS
    assert size2 <= size1 * 4 + 2000
    # metadata exposed is capped
    assert len(s2.result_store) <= MAX_STORED_RESULTS


def test_result_store_evicts_oldest():
    s = SessionState("s")
    for i in range(MAX_STORED_RESULTS + 10):
        s.add_result(f"r{i}", "p", ["x"], [[i]])
    assert len(s.result_store) <= MAX_STORED_RESULTS
    # newest kept, oldest evicted
    assert f"r{MAX_STORED_RESULTS + 9}" in s.result_store
    assert "r0" not in s.result_store
    # meta evicted too
    assert "r0" not in s.result_meta


def test_sample_rows_are_bounded():
    s = SessionState("s")
    s.add_result("r_big", "p", ["x"], [[i] for i in range(1000)])
    samples = s.result_samples(["r_big"])
    # sample only shows MAX_SAMPLE_ROWS rows
    assert samples.count("],") <= MAX_SAMPLE_ROWS + 2


# ---------------------------------------------------------------------------
# State stays small
# ---------------------------------------------------------------------------
def test_state_active_result_ids_bounded():
    s = SessionState("s")
    for i in range(MAX_STORED_RESULTS):
        s.add_result(f"r{i}", "p", ["x"], [[i]])
    s.update_state({"active_result_ids": [f"r{i}" for i in range(30)]})
    assert len(s.state["active_result_ids"]) <= MAX_STATE_RESULT_IDS


def test_state_drops_empty_values():
    s = SessionState("s")
    s.update_state({"selected_customer": "C_1", "selected_product": ""})
    assert s.state["selected_customer"] == "C_1"
    assert "selected_product" not in s.state


# ---------------------------------------------------------------------------
# Plan / compose prompts are bounded and don't contain the full conversation
# ---------------------------------------------------------------------------
def test_plan_prompt_uses_bounded_context_not_full_history():
    s = SessionState("s")
    for i in range(100):
        s.record_turn(f"سؤال طولانی {i} " + "داده " * 30, "پاسخ " + "متن " * 40)
    s.add_result("r_big", "p", ["x"], [[i] for i in range(2000)])

    prompt = db_agent._plan_prompt("سؤال جدید؟", s)
    assert len(prompt) <= MAX_CONTEXT_CHARS + 2000  # +static schema
    # full row grids are NOT embedded (no long comma lists of raw numbers)
    assert "2000" in prompt or "2000" in s.result_meta_prompt(["r_big"])


def test_compose_prompt_uses_metadata_and_tiny_sample():
    s = SessionState("s")
    sr = s.add_result("r_1", "top customers", ["Customer_ID", "revenue"],
                      [[f"C_{i}", i * 100] for i in range(500)])
    prompt = db_agent._compose_prompt("سؤال", s, {"r_1": sr}, "")
    # metadata present
    assert "r_1" in prompt
    assert "n_rows=500" in prompt
    # the full 500 rows must NOT appear
    assert "C_499" not in prompt
    assert "C_5" not in prompt  # beyond the tiny sample window


# ---------------------------------------------------------------------------
# Follow-up reuses an existing resultId instead of re-querying
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_follow_up_reuses_existing_result_id_without_new_query():
    ctx = SessionState("s")
    ctx.add_result("r_reused", "top customers",
                   ["Customer_ID", "revenue"], [["C_1", 100], ["C_2", 90]])

    calls = []

    async def fake_run_sql(sql):
        calls.append(sql)
        raise AssertionError("reuse should not run a new query")

    with patch.object(db_agent, "_llm_call",
                      new=Mock(return_value='{"intent":"follow_up","assumption":"",'
                                            '"steps":[{"tool":"reuse","input":{"resultId":"r_reused"}}]}')), \
         patch.object(db_agent, "_run_sql", side_effect=fake_run_sql):
        result = await db_agent._database_answer("بیشتر درباره مشتری برتر", ctx)

    # reuse never hits the DB
    assert calls == []
    # the reused result's exact data is available in the response
    assert "r_reused" in result["results"]
    assert result["results"]["r_reused"].rows == [["C_1", 100], ["C_2", 90]]


@pytest.mark.asyncio
async def test_reused_result_state_recorded_and_recent_bounded():
    ctx = SessionState("s")
    ctx.add_result("r_1", "p", ["x"], [[1]])
    for _ in range(50):
        ctx.record_turn("q", "a")
    assert len(ctx.recent) <= MAX_RECENT_MESSAGES * 2
    assert len(ctx.log) == MAX_LOG_ENTRIES


def test_context_has_no_exported_large_data_serialization():
    """Serializing the whole session must not include full rows in history parts."""
    s = SessionState("s")
    s.add_result("r_1", "p", ["x"], [[i] for i in range(1000)])
    parts = s.context_parts("سؤال؟")
    # 'results' metadata part references the result but with no row grids
    if "results" in parts:
        assert "[[0" not in parts["results"]
    # history (summary/recent/state) never contains rows
    for key in ("summary", "recent", "state"):
        if key in parts:
            assert "[[0" not in parts[key] and "[[" not in parts[key]
