"""Tests for order counting / quantity distinction / dedupe / huge detection."""
from backend.agents.analysis import (
    HUGE_RESULT_THRESHOLD,
    column_index,
    dedupe_order_lines,
    is_huge,
    order_count,
    quantity_sum,
    too_huge_message,
)


class TestOrderCounting:
    def test_distinct_orders(self):
        # order id column is index 0; several lines share the same order
        rows = [["T1", "line1"], ["T1", "line2"], ["T1", "line3"], ["T2", "line4"]]
        assert order_count(rows, 0) == 2

    def test_null_order_ignored(self):
        rows = [[None, "x"], ["T1", "y"]]
        assert order_count(rows, 0) == 1


class TestQuantityVsOrder:
    def test_quantity_sum(self):
        rows = [["T1", 5], ["T1", 3], ["T2", 10]]
        # 3 order lines, but 18 units sold
        assert order_count(rows, 0) == 2
        assert quantity_sum(rows, 1) == 18.0

    def test_quantity_ignores_none(self):
        rows = [["T1", None], ["T2", 7]]
        assert quantity_sum(rows, 1) == 7.0


class TestDedupe:
    def test_duplicate_order_lines_after_join(self):
        # A join duplicated each line; unique line id is index 1
        rows = [["T1", "L1"], ["T1", "L1"], ["T2", "L2"], ["T2", "L3"]]
        deduped = dedupe_order_lines(rows, 1)
        assert len(deduped) == 3
        # order count after dedupe is correct
        assert order_count(deduped, 0) == 2

    def test_null_line_id_kept_once(self):
        rows = [["T1", None], ["T1", None]]
        deduped = dedupe_order_lines(rows, 1)
        assert len(deduped) == 2  # nulls are all kept (not double-counted as same)


class TestHugeDetection:
    def test_is_huge(self):
        assert is_huge(HUGE_RESULT_THRESHOLD + 1) is True
        assert is_huge(HUGE_RESULT_THRESHOLD) is False

    def test_message_informs_user(self):
        msg = too_huge_message(5000)
        assert "5,000" in msg
        assert "بزرگ" in msg


class TestColumnIndex:
    def test_find_by_any_key(self):
        assert column_index(["a", "b", "c"], ["x", "b"]) == 1
        assert column_index(["a"], ["zzz"]) is None
