"""DuckDB MCP server.

Exposes the Customer 360 DuckDB database as Model Context Protocol tools.

Primary analytical tool:
- ``query``: execute a read-only SELECT / WITH ... SELECT and return exact
  results (resultId, columns, rows, n_rows, truncation info). resultId is
  generated server-side.

Schema discovery tools (fallback only):
- ``list_tables`` / ``get_schema``: use only when ``query`` errors on a
  column/table the LLM did not know about.

Run standalone (stdio transport):
    python -m backend.mcp.duckdb_server
"""
import json
import uuid
import warnings
from typing import Any

import duckdb
from mcp.server.fastmcp import FastMCP

from backend.config import settings

# mcp 1.29 + pydantic-settings 2.15 emit a harmless forward-reference warning
# for the FastMCP "lifespan" field. Suppress it so it doesn't pollute logs.
warnings.filterwarnings(
    "ignore",
    message="Field 'lifespan' has an incomplete definition",
    category=UserWarning,
)

mcp = FastMCP("Customer360-DuckDB")

# Allow only read-only statements. Opening the DB read-only is the hard guard;
# this keyword check is a fast first-line defence and stops multi-statement
# / DDL attempts before they reach the engine.
FORBIDDEN = (
    "insert", "update", "delete", "drop", "create", "alter", "attach",
    "detach", "copy", "set ", "call ", "pragma ", "install ", "load ",
    "export ", "import ", "vacuum", "transaction", "rollback", "begin",
)

_DEFAULT_MAX_ROWS = 1000


def _connect() -> duckdb.DuckDBPyConnection:
    # read_only=True is the authoritative write-blocker.
    con = duckdb.connect(str(settings.db_path), read_only=True)
    con.execute("SET enable_external_access=false")
    return con


def _to_json_safe(obj: Any) -> Any:
    """Return a JSON-serializable version of a query cell."""
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    try:
        json.dumps(obj)
        return obj
    except TypeError:
        return str(obj)


def _is_read_only(sql: str) -> bool:
    stripped = sql.strip().lstrip("(").strip()
    lowered = " ".join(stripped.lower().split())
    if not (lowered.startswith("select") or lowered.startswith("with ")):
        return False
    # Reject statements that smuggle a write after a leading SELECT/WITH, or
    # that contain write keywords anywhere (SELECT can't contain them legally).
    if any(kw in lowered for kw in FORBIDDEN):
        return False
    # Only allow a single statement (no semicolons beyond a trailing one).
    body = lowered.rstrip(";")
    if ";" in body:
        return False
    return True


def _execute(query: str, max_rows: int) -> dict[str, Any]:
    if not _is_read_only(query):
        return {"error": "Only single read-only SELECT / WITH ... SELECT queries are allowed."}
    con = _connect()
    try:
        # Use the cursor API (fetchall) instead of .df() so we don't require
        # numpy/pandas at runtime — only duckdb is needed.
        cur = con.execute(query)
        cols = [d[0] for d in cur.description]
        all_rows = cur.fetchall()
        total = len(all_rows)
        truncated = bool(max_rows) and total > max_rows
        out_rows = all_rows[:max_rows] if truncated else all_rows
        safe_rows = [[_to_json_safe(v) for v in r] for r in out_rows]
        return {
            "resultId": f"r_{uuid.uuid4().hex[:12]}",  # server-generated
            "columns": cols,
            "rows": safe_rows,
            "n_rows": total,              # exact full count
            "truncated": truncated,
            "returned_rows": len(safe_rows),
        }
    except duckdb.Error as e:
        return {"error": str(e)}
    finally:
        con.close()


@mcp.tool()
def query(query: str, max_rows: int = _DEFAULT_MAX_ROWS) -> str:
    """Run a read-only SQL query and return exact results as JSON.

    This is the PRIMARY analytical tool — use it for all data questions.

    Args:
        query: a single SELECT / WITH ... SELECT statement (read-only).
        max_rows: cap on rows returned (default 1000) to avoid huge payloads.

    Returns JSON:
        {resultId, columns, rows, n_rows, truncated, returned_rows}
    resultId is generated server-side; reference it in UI blocks instead of
    copying the data.

    Do DB-side filtering/aggregation/grouping/sorting/LIMIT in the SQL — never
    request a huge raw result and analyse it yourself. Prefer:
        SELECT ..., COUNT(DISTINCT "شماره فاکتور") AS orders, SUM("مقدار") AS units
    from the sales table to keep order vs line vs quantity correct.
    """
    return json.dumps(_execute(query, max_rows), ensure_ascii=False)


@mcp.tool()
def run_sql(query: str, max_rows: int = _DEFAULT_MAX_ROWS) -> str:
    """Alias of ``query`` for backward compatibility."""
    return json.dumps(_execute(query, max_rows), ensure_ascii=False)


@mcp.tool()
def list_tables() -> str:
    """[fallback] List all tables with row counts. Prefer the static schema."""
    con = _connect()
    try:
        rows = []
        for t, _ in _tables(con):
            cnt = con.execute(f'SELECT count(*) FROM "{t}"').fetchone()[0]
            ncols = con.execute(
                f"SELECT count(*) FROM information_schema.columns "
                f"WHERE table_name='{t}' AND table_schema='main'"
            ).fetchone()[0]
            rows.append({"table": t, "rows": int(cnt), "columns": int(ncols)})
        return json.dumps(rows, ensure_ascii=False)
    finally:
        con.close()


@mcp.tool()
def get_schema(table: str = "") -> str:
    """[fallback] Return the column schema (or all tables). Prefer static schema."""
    con = _connect()
    try:
        tables = [table] if table else [t for t, _ in _tables(con)]
        out = []
        for t in tables:
            try:
                cols = con.execute(
                    f'SELECT column_name, data_type FROM information_schema.columns '
                    f"WHERE table_name='{t}' AND table_schema='main' ORDER BY ordinal_position"
                ).fetchall()
            except duckdb.Error:
                out.append({"table": t, "error": "not found"})
                continue
            sample = con.execute(f'SELECT * FROM "{t}" LIMIT 2').fetchall()
            out.append({
                "table": t,
                "columns": [{"name": c[0], "type": c[1]} for c in cols],
                "sample_rows": [[_to_json_safe(v) for v in row] for row in sample],
                "column_names": [c[0] for c in cols],
            })
        return json.dumps(out, ensure_ascii=False)
    finally:
        con.close()


def _tables(con: duckdb.DuckDBPyConnection) -> list[tuple[str, str]]:
    return con.execute(
        "SELECT table_name, table_schema FROM information_schema.tables "
        "WHERE table_schema='main' ORDER BY 1"
    ).fetchall()


if __name__ == "__main__":
    mcp.run(transport="stdio")
