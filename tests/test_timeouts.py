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


# ---------------------------------------------------------------------------
# Engine recommendations must reach the Persian chat answer in Persian.
# The engine keeps canonical English internally, so every user-facing boundary
# translates; the chat path is one and used to leak English through.
# ---------------------------------------------------------------------------
def test_crm_payload_is_localized_at_the_chat_boundary():
    payload = {
        "customer_id": "C_1",
        "next_best_actions": [{
            "action_id": "SERVICE_RECOVERY",
            "name": "Service recovery",
            "reason": "2 bounced cheque(s)",
            "suggested_next_step":
                "Resolve the complaint and confirm satisfaction before "
                "proposing any additional sales.",
        }],
    }
    out = db_agent._localize_crm(payload)
    action = out["next_best_actions"][0]

    assert action["action_id"] == "SERVICE_RECOVERY"  # ids untouched
    for field in ("name", "reason", "suggested_next_step"):
        assert not any(c.isascii() and c.isalpha() for c in action[field]), \
            f"{field} still contains English: {action[field]!r}"


def test_localization_preserves_non_string_values():
    """Only human-readable keys are translated; logic fields stay intact."""
    out = db_agent._localize_crm(
        {"action_id": "X", "priority": 3, "score": 0.42, "flags": [1, 2]}
    )
    assert out["priority"] == 3
    assert out["score"] == 0.42
    assert out["flags"] == [1, 2]


def test_localization_is_idempotent():
    """Re-translating already-Persian text must not corrupt it."""
    once = db_agent._localize_crm({"reason": "2 bounced cheque(s)"})
    twice = db_agent._localize_crm(once)
    assert once == twice


# ---------------------------------------------------------------------------
# A bounded call must degrade the answer, never blank it out. The first cut of
# these timeouts aborted the whole reply and — because asyncio.TimeoutError
# stringifies to "" — surfaced as a message that stopped mid-sentence:
#   "خطا در دریافت اطلاعات مشتری:"
# ---------------------------------------------------------------------------
def test_timeout_note_is_never_empty():
    note = db_agent._exc_note(asyncio.TimeoutError())
    assert note.strip(), "a timeout must still explain itself to the user"
    assert "طولانی" in note


def test_exc_note_uses_the_real_message_when_there_is_one():
    assert "boom" in db_agent._exc_note(RuntimeError("boom"))


def test_exc_note_is_blank_only_for_a_silent_exception():
    assert db_agent._exc_note(RuntimeError("")) == ""


def test_crm_timeout_ceiling_clears_measured_tool_latency():
    """top_at_risk_customers measured ~25s on a cold cache; a ceiling near that
    fired on healthy work. The bound is for hangs, not normal slowness."""
    assert db_agent.CRM_TOOL_TIMEOUT_S >= 60
    assert db_agent.LLM_TIMEOUT_S >= 30
