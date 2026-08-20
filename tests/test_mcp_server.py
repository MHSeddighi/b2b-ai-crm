"""Tests for the DuckDB MCP layer: query tool, resultId, read-only, schema."""
import json

import duckdb
import pytest

from backend.mcp import duckdb_server
from backend.mcp.schema_context import (
    CUSTOMER360_SCHEMA,
    CUSTOMER360_RELATIONSHIPS,
    TABLES,
)


def _call_query(query: str, max_rows: int = 1000) -> dict:
    return json.loads(duckdb_server.query(query, max_rows=max_rows))


class TestQueryTool:
    def test_query_generates_result_id_server_side(self):
        r1 = _call_query("SELECT count(*) AS n FROM customers")
        r2 = _call_query("SELECT count(*) AS n FROM customers")
        assert r1["resultId"]
        assert r1["resultId"] != r2["resultId"], "resultId must be unique per call"

    def test_query_returns_exact_columns_rows_count(self):
        r = _call_query("SELECT Customer_ID, Customer_Status FROM customers LIMIT 3")
        assert r["columns"] == ["Customer_ID", "Customer_Status"]
        assert len(r["rows"]) == 3
        assert r["n_rows"] == 3
        assert r["returned_rows"] == 3
        assert r["truncated"] is False

    def test_query_is_strictly_read_only(self):
        for sql in ["DELETE FROM customers", "INSERT INTO customers VALUES ('x')",
                    "DROP TABLE customers", "UPDATE customers SET Customer_Status='فعال'"]:
            r = _call_query(sql)
            assert "error" in r, f"write query {sql!r} must be rejected"

    def test_query_blocks_attached_external_access(self):
        r = _call_query("SELECT * FROM read_csv_auto('/etc/hostname')")
        assert "error" in r

    def test_query_truncation_info(self):
        r = _call_query("SELECT * FROM sales", max_rows=5)
        assert r["n_rows"] == 52987
        assert len(r["rows"]) == 5
        assert r["returned_rows"] == 5
        assert r["truncated"] is True

    def test_query_returns_exact_db_values(self):
        r = _call_query("SELECT count(DISTINCT Customer_ID) AS n FROM sales")
        assert r["rows"][0][0] == 644

    def test_empty_result(self):
        r = _call_query("SELECT 1 AS x WHERE 1=0")
        assert r["n_rows"] == 0
        assert r["rows"] == []
        assert r["truncated"] is False


class TestOrderGranularity:
    """Order vs order-line vs quantity must never be conflated (via SQL)."""

    def test_order_count_is_distinct(self):
        r = _call_query('SELECT count(DISTINCT "شماره فاکتور") AS orders FROM sales')
        assert r["rows"][0][0] == 14423  # invoices header count

    def test_line_count_is_rows(self):
        r = _call_query('SELECT count(*) AS lines FROM sales')
        assert r["rows"][0][0] == 52987

    def test_quantity_sum(self):
        r = _call_query('SELECT round(sum("مقدار"),0) AS qty FROM sales')
        assert r["rows"][0][0] > 0
        assert r["rows"][0][0] != 14423 and r["rows"][0][0] != 52987

    def test_no_duplicate_orders_after_join(self):
        # joining sales->realized_costs must not multiply distinct order count
        r = _call_query(
            'SELECT count(DISTINCT s."شماره فاکتور") AS orders FROM sales s '
            'LEFT JOIN realized_costs c ON s.Sales_Line_ID = c.Sales_Line_ID'
        )
        assert r["rows"][0][0] == 14423


class TestSchemaContext:
    def test_schema_contains_all_tables(self):
        for t in TABLES:
            assert t in CUSTOMER360_SCHEMA

    def test_schema_has_relationships(self):
        assert "Customer_ID" in CUSTOMER360_RELATIONSHIPS
        assert "sales" in CUSTOMER360_RELATIONSHIPS.lower()

    def test_schema_mentions_order_rules(self):
        assert "COUNT(DISTINCT" in CUSTOMER360_SCHEMA or "distinct" in CUSTOMER360_SCHEMA.lower()
