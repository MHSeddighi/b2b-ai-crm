"""Shared, validated Block schema for copilot responses.

This is the strict UI contract between the LLM/backend and the frontend.
An assistant response is an ordered array of ``blocks`` plus a ``results`` map
of MCP query results referenced by ``resultId``.

The frontend mirrors these types in TypeScript (see frontend/src/lib/blocks.ts).
"""
from __future__ import annotations

from typing import Any, Literal, Union

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

# ---------------------------------------------------------------------------
# Structured result (as returned by the MCP run_sql tool)
# ---------------------------------------------------------------------------
class SqlResult(BaseModel):
    resultId: str
    columns: list[str]
    rows: list[list[Any]]
    n_rows: int = Field(default=0)

    @model_validator(mode="after")
    def _sync_count(self) -> "SqlResult":
        if not self.n_rows:
            self.n_rows = len(self.rows)
        return self


# ---------------------------------------------------------------------------
# Blocks
# ---------------------------------------------------------------------------
class BaseBlock(BaseModel):
    id: str = Field(..., min_length=1)
    type: str


class MarkdownBlock(BaseBlock):
    type: Literal["markdown"]
    content: str


class MetricBlock(BaseBlock):
    type: Literal["metric"]
    resultId: str | None = None
    label: str
    valueKey: str | None = None  # column to read the value from
    rowIndex: int = 0
    change: str | None = None
    trend: Literal["up", "down", "neutral"] | None = None


class ChartBlock(BaseBlock):
    type: Literal["chart"]
    resultId: str
    chartType: Literal["line", "bar", "scatter"]
    xKey: str | None = None
    series: list[dict[str, str]] = Field(default_factory=list)  # [{"dataKey","label"}]
    title: str | None = None


class HistogramBlock(BaseBlock):
    type: Literal["histogram"]
    resultId: str
    dataKey: str
    bins: int = 10
    title: str | None = None


class TableBlock(BaseBlock):
    type: Literal["table"]
    resultId: str | None = None
    columns: list[str] | None = None
    rows: list[list[Any]] | None = None
    title: str | None = None


class RecommendationBlock(BaseBlock):
    type: Literal["recommendation"]
    resultId: str | None = None
    title: str | None = None
    text: str
    reason: str | None = None


class CustomerCardBlock(BaseBlock):
    type: Literal["customer_card"]
    resultId: str | None = None
    customerId: str


class ProductCardBlock(BaseBlock):
    type: Literal["product_card"]
    resultId: str | None = None
    productId: str


class OrderCardBlock(BaseBlock):
    type: Literal["order_card"]
    resultId: str | None = None
    orderId: str


Block = Union[
    MarkdownBlock,
    MetricBlock,
    ChartBlock,
    HistogramBlock,
    TableBlock,
    RecommendationBlock,
    CustomerCardBlock,
    ProductCardBlock,
    OrderCardBlock,
]

BLOCK_TYPES = {
    "markdown", "metric", "chart", "histogram", "table",
    "recommendation", "customer_card", "product_card", "order_card",
}


class ChatResponse(BaseModel):
    """The full assistant reply: ordered blocks + a results map keyed by resultId."""

    blocks: list[Block] = Field(default_factory=list)
    results: dict[str, SqlResult] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def validate_blocks(raw: Any) -> list[Block]:
    """Validate raw LLM-produced blocks, dropping malformed/unknown ones.

    Never raises; malformed entries are replaced with a safe markdown fallback
    so an unknown block cannot crash rendering.
    """
    if not isinstance(raw, list):
        return []
    out: list[Block] = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            continue
        btype = item.get("type")
        if btype not in BLOCK_TYPES:
            continue
        # guaranteed id
        item = dict(item)
        item.setdefault("id", f"b{i}")
        try:
            block = _construct(btype, item)
            out.append(block)
        except (ValidationError, TypeError, ValueError):
            continue
    return out


def _construct(btype: str, item: dict[str, Any]) -> Block:
    model: type[BaseModel] = {
        "markdown": MarkdownBlock,
        "metric": MetricBlock,
        "chart": ChartBlock,
        "histogram": HistogramBlock,
        "table": TableBlock,
        "recommendation": RecommendationBlock,
        "customer_card": CustomerCardBlock,
        "product_card": ProductCardBlock,
        "order_card": OrderCardBlock,
    }[btype]
    return model(**item)


def blocks_from_dicts(raw: list[dict[str, Any]]) -> ChatResponse:
    """Build a ChatResponse from raw blocks + results dicts (loose input)."""
    return ChatResponse(blocks=validate_blocks(raw), results={})
