# Budget Planner MCP Server

An [MCP](https://modelcontextprotocol.io) server that wraps the Budget Planner
**backend** REST API as tools, so MCP clients (the Telegram bot, MCP Inspector,
Claude, etc.) can interact with the backend through tool calls.

It runs over **streamable HTTP**. Clients connect at:

```
http://<MCP_HOST>:<MCP_PORT>/mcp        # default: http://localhost:8001/mcp
```

## How it works

`server.py` defines one tool per backend endpoint (`backend/routers/*.py`) using
`FastMCP`. Each tool calls the backend via `backend_client.py`, a small async
`httpx` wrapper with a request timeout and structured, model-readable errors
(`{"ok": false, "status_code", "error", "details"}`) so the agent can self-correct.

Timestamps default to "now" (UTC, ISO-8601) when omitted.

## Configuration

Use the centralized `backend/.env` file. Copy `backend/.env.example` to
`backend/.env` and adjust:

| Variable | Default | Description |
| --- | --- | --- |
| `BACKEND_API_BASE_URL` | `http://localhost:8000` | Backend base URL |
| `BACKEND_REQUEST_TIMEOUT` | `10.0` | Per-request timeout (seconds) |
| `MCP_HOST` | `0.0.0.0` | Listen host |
| `MCP_PORT` | `8001` | Listen port |

## Running

Locally, from `backend/`:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m mcp_server.server
```

With Docker Compose (from the repo root), the `mcp_server` service uses the
same backend image and starts after the backend. Start order is always:
**backend (8000) -> mcp_server (8001) -> bot**.

## Inspecting the tools

```bash
npx @modelcontextprotocol/inspector
# then connect to http://localhost:8001/mcp (transport: Streamable HTTP)
```

## Available tools

- **Accounts:** `list_accounts`, `create_account`, `update_account`,
  `delete_account`, `update_account_balance`, `transfer_funds`
- **Expenses:** `create_expense`, `list_expenses`, `expense_dashboard`,
  `update_expense`, `delete_expense`
- **Income:** `create_income`, `list_income`, `income_dashboard`,
  `update_income`, `delete_income`
- **Loans:** `create_loan_account`, `list_loan_accounts`, `update_loan_account`,
  `delete_loan_account`, `create_loan_transaction`, `list_loan_transactions`,
  `delete_loan_transaction`, `loan_dashboard`
- **Investments:** `create_investment_account`, `list_investment_accounts`,
  `update_investment_account`, `delete_investment_account`,
  `create_investment_transaction`, `list_investment_transactions`,
  `update_investment_transaction`, `delete_investment_transaction`
- **Wishlist:** `create_wishlist_item`, `list_wishlist_items`,
  `update_wishlist_item`, `delete_wishlist_item`, `buy_wishlist_item`

Destructive/money-moving tools carry confirmation guidance in their descriptions;
the bot's system prompt enforces asking the user before risky actions.
