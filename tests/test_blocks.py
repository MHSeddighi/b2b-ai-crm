"""Unit tests for the shared Block schema and validation."""
import pytest
from pydantic import ValidationError

from backend.schemas.blocks import (
    BLOCK_TYPES,
    ChatResponse,
    ChartBlock,
    CustomerCardBlock,
    MarkdownBlock,
    MetricBlock,
    OrderCardBlock,
    ProductCardBlock,
    SqlResult,
    validate_blocks,
)


class TestMarkdownOnly:
    def test_single_markdown(self):
        blocks = validate_blocks([{"type": "markdown", "content": "## سلام\n\nمتن"}])
        assert len(blocks) == 1
        assert isinstance(blocks[0], MarkdownBlock)
        assert blocks[0].content.startswith("## سلام")


class TestMarkdownMetric:
    def test_markdown_then_metric(self):
        raw = [
            {"type": "markdown", "content": "intro"},
            {"type": "metric", "label": "رشد فروش", "resultId": "r1", "valueKey": "growth"},
        ]
        blocks = validate_blocks(raw)
        assert [b.type for b in blocks] == ["markdown", "metric"]
        assert isinstance(blocks[1], MetricBlock)


class TestMarkdownChartMarkdown:
    def test_order(self):
        raw = [
            {"type": "markdown", "content": "a"},
            {"type": "chart", "resultId": "r1", "chartType": "line", "xKey": "month", "series": [{"dataKey": "sales", "label": "فروش"}]},
            {"type": "markdown", "content": "b"},
        ]
        blocks = validate_blocks(raw)
        assert [b.type for b in blocks] == ["markdown", "chart", "markdown"]


class TestMarkdownMetricChartRecommendation:
    def test_full_pipeline(self):
        raw = [
            {"type": "markdown", "content": "m1"},
            {"type": "metric", "label": "X", "resultId": "r1"},
            {"type": "chart", "resultId": "r1", "chartType": "bar"},
            {"type": "recommendation", "text": "do this"},
        ]
        blocks = validate_blocks(raw)
        assert [b.type for b in blocks] == ["markdown", "metric", "chart", "recommendation"]


class TestArbitraryOrdering:
    def test_any_order_kept(self):
        raw = [
            {"type": "customer_card", "customerId": "C_1"},
            {"type": "markdown", "content": "x"},
            {"type": "table", "columns": ["a"], "rows": [[1]]},
            {"type": "markdown", "content": "y"},
            {"type": "metric", "label": "L"},
        ]
        blocks = validate_blocks(raw)
        assert [b.type for b in blocks] == ["customer_card", "markdown", "table", "markdown", "metric"]


class TestResultIdReference:
    def test_chart_references_result(self):
        res = SqlResult(resultId="r1", columns=["month", "sales"], rows=[["m1", 10], ["m2", 20]])
        resp = ChatResponse(
            blocks=validate_blocks([
                {"type": "chart", "resultId": "r1", "chartType": "line", "xKey": "month", "series": [{"dataKey": "sales"}]}
            ]),
            results={"r1": res},
        )
        assert resp.results["r1"].rows == [["m1", 10], ["m2", 20]]

    def test_unknown_result_reference_ok_in_schema(self):
        blocks = validate_blocks([{"type": "table", "resultId": "missing"}])
        assert blocks[0].resultId == "missing"


class TestCards:
    def test_all_cards(self):
        raw = [
            {"type": "customer_card", "customerId": "C_1"},
            {"type": "product_card", "productId": "P_1"},
            {"type": "order_card", "orderId": "T_1"},
        ]
        blocks = validate_blocks(raw)
        assert isinstance(blocks[0], CustomerCardBlock)
        assert isinstance(blocks[1], ProductCardBlock)
        assert isinstance(blocks[2], OrderCardBlock)


class TestInvalidBlocks:
    def test_unknown_type_dropped(self):
        blocks = validate_blocks([{"type": "nonsense", "content": "x"}, {"type": "markdown", "content": "ok"}])
        assert [b.type for b in blocks] == ["markdown"]

    def test_malformed_dropped(self):
        # chart requires resultId
        blocks = validate_blocks([{"type": "chart", "chartType": "line"}])
        assert blocks == []

    def test_missing_id_gets_default(self):
        blocks = validate_blocks([{"type": "markdown", "content": "hi"}])
        assert blocks[0].id == "b0"

    def test_not_a_list(self):
        assert validate_blocks({"type": "markdown"}) == []

    def test_non_dict_items_skipped(self):
        blocks = validate_blocks(["hello", 5, {"type": "markdown", "content": "ok"}])
        assert [b.type for b in blocks] == ["markdown"]
