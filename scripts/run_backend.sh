#!/usr/bin/env bash
# Start the Customer 360 backend (FastAPI + DuckDB MCP + LLM agent).
# Usage: scripts/run_backend.sh
set -euo pipefail
cd "$(dirname "$0")/.."

# Load .env if present
if [ -f .env ]; then
  set -a
  source .env
  set +a
fi

HOST="${BACKEND_HOST:-127.0.0.1}"
PORT="${BACKEND_PORT:-8000}"

# Use the venv if available, else system python
if [ -d .venv ] && [ -x .venv/bin/python ]; then
  PY=.venv/bin/python
else
  PY=python3
fi

echo "Starting Customer 360 backend on http://${HOST}:${PORT}"
echo "DB: ${CUSTOMER360_DB:-data/processed/customer_360.duckdb}  LLM provider: ${LLM_PROVIDER:-openai}"
exec "$PY" -m uvicorn backend.main:app --host "$HOST" --port "$PORT" --reload
