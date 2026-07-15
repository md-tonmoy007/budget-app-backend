#!/bin/sh
set -eu

PORT="${PORT:-8000}"
MCP_PORT="${MCP_PORT:-8001}"

export BACKEND_API_BASE_URL="${BACKEND_API_BASE_URL:-http://127.0.0.1:${PORT}}"
export BUDGET_API_BASE_URL="${BUDGET_API_BASE_URL:-http://127.0.0.1:${PORT}}"
export MCP_HOST="${MCP_HOST:-127.0.0.1}"
export MCP_PORT
export MCP_SERVER_URL="${MCP_SERVER_URL:-http://127.0.0.1:${MCP_PORT}/mcp}"

uvicorn main:app --host 0.0.0.0 --port "${PORT}" &
backend_pid="$!"

python -m mcp_server.server &
mcp_pid="$!"

python -m telegram_bot.src.bot.main &
bot_pid="$!"

term() {
  kill "$backend_pid" "$mcp_pid" "$bot_pid" 2>/dev/null || true
}
trap term INT TERM

wait -n "$backend_pid" "$mcp_pid" "$bot_pid"
status="$?"
term
wait 2>/dev/null || true
exit "$status"
