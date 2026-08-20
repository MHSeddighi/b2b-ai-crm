"""Unit tests for the deterministic recommendation signals.

``run_sql`` is faked, so these assert the signal logic itself (thresholds,
wording, must-mention extraction, injection guard) without touching DuckDB.
"""
import pytest

from backend.agents import recommend
from backend.agents.recommend import customer_signals, product_signals


def _sql_router(mapping, default=None):
    """Fake run_sql dispatching on a substring of the query."""
    async def run_sql(sql: str):
        for needle, rows in mapping.items():
            if needle in sql:
                return {"rows": rows, "columns": [], "n_rows": len(rows)}
        return {"rows": default or [], "columns": [], "n_rows": 0}
    return run_sql


@pytest.mark.asyncio
@pytest.mark.parametrize("bad_id", ["x'; DROP TABLE sales; --", "a b", "", "x" * 40])
async def test_unsafe_ids_are_rejected_before_any_query(bad_id):
    """Ids reach us from model output, so anything off-pattern must not be
    interpolated into SQL at all."""
    called = False

    async def run_sql(sql):
        nonlocal called
        called = True
        return {"rows": []}

    assert await customer_signals(bad_id, run_sql) == ""
    assert await product_signals(bad_id, run_sql) == ""
    assert called is False


@pytest.mark.asyncio
async def test_customer_signals_report_headroom_and_credit_risk():
    run_sql = _sql_router({
        "wallet_share": [["2022-06", 3471.0, 1423.1, 2047.9, 41.0, "رقیب X"]],
        "collections": [[259, 23.9, 53, 2]],
    })
    out = await customer_signals("C_683666", run_sql)

    assert "41% share" in out
    assert "رقیب X" in out
    # a bounced cheque must surface as an explicit credit-risk flag
    assert "credit risk" in out
    # the competitor and the gap are what make the advice actionable
    assert "MUST appear" in out
    assert "رقیب X" in out.split("MUST appear")[1]


@pytest.mark.asyncio
async def test_overdue_customer_is_flagged_against_their_own_rhythm():
    """A gap far past the customer's normal cadence is a re-activation case."""
    run_sql = _sql_router({"DISTINCT CAST": [[97, 8.9, "2022-06-06", 1507]]})
    out = await customer_signals("C_1", run_sql)
    assert "overdue" in out.lower()


@pytest.mark.asyncio
async def test_regular_customer_is_not_flagged_overdue():
    run_sql = _sql_router({"DISTINCT CAST": [[97, 30.0, "2022-06-06", 12]]})
    out = await customer_signals("C_1", run_sql)
    assert "overdue" not in out.lower()
    assert "normal rhythm" in out


@pytest.mark.asyncio
async def test_thin_margin_warns_against_discounting():
    run_sql = _sql_router({"realized_costs": [[203.1, 189.1, 6.9]]})
    out = await product_signals("P_1", run_sql)
    assert "thin" in out.lower()
    assert "margin 6.9%" in out


@pytest.mark.asyncio
async def test_healthy_margin_allows_discount_room():
    run_sql = _sql_router({"realized_costs": [[300.0, 150.0, 50.0]]})
    out = await product_signals("P_1", run_sql)
    assert "room to discount" in out


@pytest.mark.asyncio
async def test_product_signals_surface_closing_discount_and_whitespace():
    run_sql = _sql_router({
        "FROM offers": [["قبول", 115, 4.5], ["رد", 101, 5.0]],
        "fam_buyers": [[162]],
    })
    out = await product_signals("P_RARE_Product_Family_03", run_sql)

    assert "Accept rate" in out
    assert "162 customers already buy" in out
    must = out.split("MUST appear")[1]
    assert "4.5% discount" in must
    assert "162 untapped" in must


@pytest.mark.asyncio
async def test_declining_demand_is_called_out_with_direction():
    run_sql = _sql_router({
        "strftime": [["2022", 268111, 62], ["2021", 1169506, 139]],
    })
    out = await product_signals("P_1", run_sql)
    assert "DOWN" in out
    assert "77.1%" in out


@pytest.mark.asyncio
async def test_a_failing_signal_does_not_sink_the_others():
    """One broken query must degrade that signal only, not the whole block."""
    async def run_sql(sql):
        if "wallet_share" in sql:
            raise RuntimeError("boom")
        if "collections" in sql:
            return {"rows": [[10, 2.0, 5, 0]]}
        return {"rows": []}

    out = await customer_signals("C_1", run_sql)
    assert "COLLECTION" in out
    assert "HEADROOM" not in out


@pytest.mark.asyncio
async def test_no_data_yields_no_block_rather_than_empty_headings():
    run_sql = _sql_router({})
    assert await product_signals("P_missing", run_sql) == ""


def test_open_status_constants_match_the_dataset_values():
    """These strings are matched against real column values — a typo would
    silently report every customer as having no open items."""
    assert "درحال بررسی" in recommend.OPEN_COMPLAINT_STATUSES
    assert "درحال بررسی" in recommend.OPEN_REQUEST_STATUSES
    assert "درحال توسعه" in recommend.OPEN_REQUEST_STATUSES
