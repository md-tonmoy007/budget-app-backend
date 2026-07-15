"""MCP server exposing the Budget Planner backend API as tools.

Runs over streamable HTTP so the Telegram bot (or any MCP client) can connect at
http://<host>:<port>/mcp. Each tool wraps one backend REST endpoint. Tool
docstrings are what the LLM sees, so they are written as action-oriented
instructions and carry the safety/confirmation policy for destructive actions.
"""
import os
from datetime import date, datetime, timezone
from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP

from .backend_client import BackendClient

MCP_HOST = os.getenv("MCP_HOST", "0.0.0.0")
MCP_PORT = int(os.getenv("MCP_PORT", "8001"))

mcp = FastMCP("budget-planner", host=MCP_HOST, port=MCP_PORT)
backend = BackendClient()


def now_iso() -> str:
    """Current timestamp as an ISO-8601 string (UTC)."""
    return datetime.now(timezone.utc).isoformat()


def today_iso() -> str:
    """Today's date as an ISO-8601 date string."""
    return date.today().isoformat()


def _clean(data: Dict[str, Any]) -> Dict[str, Any]:
    """Drop keys whose value is None so we never overwrite backend defaults."""
    return {k: v for k, v in data.items() if v is not None}


# ---------------------------------------------------------------------------
# Accounts
# ---------------------------------------------------------------------------

@mcp.tool()
async def list_accounts() -> Any:
    """List all asset accounts (Cash, Bank, Credit Card) with their balances.
    Use this to resolve an account name to its id before any action that needs one."""
    return await backend.get("/accounts/")


@mcp.tool()
async def create_account(name: str, type: str, balance: float = 0.0) -> Any:
    """Create a new asset account. `type` is typically 'Cash', 'Bank', or 'Credit Card'."""
    return await backend.post("/accounts/", json={"name": name, "type": type, "balance": balance})


@mcp.tool()
async def update_account(account_id: int, name: Optional[str] = None,
                         type: Optional[str] = None, balance: Optional[float] = None) -> Any:
    """Update an account's name, type, or balance. CONFIRM with the user first if this
    changes the balance, and only act when the target account is unambiguous."""
    return await backend.put(f"/accounts/{account_id}",
                             json=_clean({"name": name, "type": type, "balance": balance}))


@mcp.tool()
async def delete_account(account_id: int) -> Any:
    """Delete an asset account. DESTRUCTIVE: only call after the user has explicitly
    confirmed deletion of the specific account."""
    return await backend.delete(f"/accounts/{account_id}")


@mcp.tool()
async def update_account_balance(account_id: int, amount: float) -> Any:
    """Adjust an account's balance by `amount` (positive adds, negative subtracts).
    DIRECTLY CHANGES MONEY: always confirm with the user before calling."""
    return await backend.put(f"/accounts/{account_id}/balance", params={"amount": amount})


@mcp.tool()
async def transfer_funds(from_account_id: int, to_account_id: int, amount: float,
                         description: Optional[str] = None) -> Any:
    """Transfer money between two accounts. MOVES MONEY: confirm the resolved source
    account, destination account, and amount with the user before calling if any of
    them is ambiguous."""
    return await backend.post("/accounts/transfer", json=_clean({
        "from_account_id": from_account_id,
        "to_account_id": to_account_id,
        "amount": amount,
        "description": description,
    }))


# ---------------------------------------------------------------------------
# Expenses
# ---------------------------------------------------------------------------

@mcp.tool()
async def create_expense(amount: float, expense_type: str, account_id: int,
                         description: Optional[str] = None, datetime: Optional[str] = None) -> Any:
    """Record a new expense and deduct it from the given account. May be executed
    directly when the amount and expense_type are clear. `datetime` defaults to now."""
    return await backend.post("/expenses/", json=_clean({
        "amount": amount,
        "expense_type": expense_type,
        "account_id": account_id,
        "description": description,
        "datetime": datetime or now_iso(),
    }))


@mcp.tool()
async def list_expenses(skip: int = 0, limit: int = 100) -> Any:
    """List recorded expenses (most recent first), each including its account name."""
    return await backend.get("/expenses/", params={"skip": skip, "limit": limit})


@mcp.tool()
async def expense_dashboard() -> Any:
    """Get the current month's total expenses and the 5 most recent expenses."""
    return await backend.get("/expenses/dashboard")


@mcp.tool()
async def update_expense(expense_id: int, amount: Optional[float] = None,
                         expense_type: Optional[str] = None, account_id: Optional[int] = None,
                         description: Optional[str] = None, datetime: Optional[str] = None) -> Any:
    """Update an existing expense (balances are re-synced by the backend). Only call
    after the user clearly identifies the expense; otherwise confirm first."""
    return await backend.put(f"/expenses/{expense_id}", json=_clean({
        "amount": amount, "expense_type": expense_type, "account_id": account_id,
        "description": description, "datetime": datetime,
    }))


@mcp.tool()
async def delete_expense(expense_id: int) -> Any:
    """Delete an expense and refund its amount to the account. DESTRUCTIVE: only call
    after the user has explicitly confirmed the specific expense to delete."""
    return await backend.delete(f"/expenses/{expense_id}")


# ---------------------------------------------------------------------------
# Income
# ---------------------------------------------------------------------------

@mcp.tool()
async def create_income(amount: float, income_type: str, account_id: int,
                        description: Optional[str] = None, datetime: Optional[str] = None) -> Any:
    """Record new income and add it to the given account. May be executed directly
    when the amount and income_type are clear. `datetime` defaults to now."""
    return await backend.post("/income/", json=_clean({
        "amount": amount,
        "income_type": income_type,
        "account_id": account_id,
        "description": description,
        "datetime": datetime or now_iso(),
    }))


@mcp.tool()
async def list_income(skip: int = 0, limit: int = 100) -> Any:
    """List recorded income (most recent first), each including its account name."""
    return await backend.get("/income/", params={"skip": skip, "limit": limit})


@mcp.tool()
async def income_dashboard() -> Any:
    """Get the current month's total income and the 5 most recent income records."""
    return await backend.get("/income/dashboard")


@mcp.tool()
async def update_income(income_id: int, amount: Optional[float] = None,
                        income_type: Optional[str] = None, account_id: Optional[int] = None,
                        description: Optional[str] = None, datetime: Optional[str] = None) -> Any:
    """Update an existing income record (balances are re-synced). Only call after the
    user clearly identifies the record; otherwise confirm first."""
    return await backend.put(f"/income/{income_id}", json=_clean({
        "amount": amount, "income_type": income_type, "account_id": account_id,
        "description": description, "datetime": datetime,
    }))


@mcp.tool()
async def delete_income(income_id: int) -> Any:
    """Delete an income record and remove its amount from the account. DESTRUCTIVE:
    only call after the user has explicitly confirmed the specific record."""
    return await backend.delete(f"/income/{income_id}")


# ---------------------------------------------------------------------------
# Loans
# ---------------------------------------------------------------------------

@mcp.tool()
async def create_loan_account(name: str, type: str, balance: float = 0.0,
                              status: str = "ACTIVE") -> Any:
    """Create a loan account for a person/institution. `type` is 'GIVEN' (you lent)
    or 'TAKEN' (you borrowed). `balance` is the outstanding amount."""
    return await backend.post("/loans/accounts", json={
        "name": name, "type": type, "balance": balance, "status": status,
    })


@mcp.tool()
async def list_loan_accounts() -> Any:
    """List all loan accounts with their type, outstanding balance, and status."""
    return await backend.get("/loans/accounts")


@mcp.tool()
async def update_loan_account(account_id: int, name: str, type: str, status: str) -> Any:
    """Update a loan account's name, type ('GIVEN'/'TAKEN'), and status
    ('ACTIVE'/'SETTLED'). Confirm first unless the account is unambiguous."""
    return await backend.put(f"/loans/accounts/{account_id}",
                             json={"name": name, "type": type, "status": status})


@mcp.tool()
async def delete_loan_account(account_id: int) -> Any:
    """Delete a loan account and ALL its transactions. DESTRUCTIVE: only call after
    explicit user confirmation of the specific loan account."""
    return await backend.delete(f"/loans/accounts/{account_id}")


@mcp.tool()
async def create_loan_transaction(loan_account_id: int, type: str, amount: float,
                                  asset_account_id: Optional[int] = None,
                                  description: Optional[str] = None,
                                  date: Optional[str] = None) -> Any:
    """Record a loan transaction. `type` is 'PRINCIPAL' (new lending/borrowing) or
    'REPAYMENT'. Pass `asset_account_id` to also move money in that asset account.
    `date` defaults to now."""
    return await backend.post("/loans/transactions", json=_clean({
        "loan_account_id": loan_account_id,
        "type": type,
        "amount": amount,
        "asset_account_id": asset_account_id,
        "description": description,
        "date": date or now_iso(),
    }))


@mcp.tool()
async def list_loan_transactions(account_id: Optional[int] = None) -> Any:
    """List loan transactions (most recent first). Optionally filter by loan account id."""
    params = {"account_id": account_id} if account_id is not None else None
    return await backend.get("/loans/transactions", params=params)


@mcp.tool()
async def delete_loan_transaction(transaction_id: int) -> Any:
    """Delete a loan transaction and reverse its balance effects. DESTRUCTIVE: only
    call after explicit user confirmation of the specific transaction."""
    return await backend.delete(f"/loans/transactions/{transaction_id}")


@mcp.tool()
async def loan_dashboard() -> Any:
    """Get loan summary: total_given, total_taken, and net_position across active loans."""
    return await backend.get("/loans/dashboard")


# ---------------------------------------------------------------------------
# Investments
# ---------------------------------------------------------------------------

@mcp.tool()
async def create_investment_account(company_name: str, agent_name: str,
                                    status: str = "ACTIVE") -> Any:
    """Create an investment account for a company/agent."""
    return await backend.post("/investments/accounts", json={
        "company_name": company_name, "agent_name": agent_name, "status": status,
    })


@mcp.tool()
async def list_investment_accounts() -> Any:
    """List all investment accounts."""
    return await backend.get("/investments/accounts")


@mcp.tool()
async def update_investment_account(account_id: int, company_name: str, agent_name: str,
                                    status: str) -> Any:
    """Update an investment account's company_name, agent_name, and status
    ('ACTIVE'/'CLOSED'). Confirm first unless the account is unambiguous."""
    return await backend.put(f"/investments/accounts/{account_id}", json={
        "company_name": company_name, "agent_name": agent_name, "status": status,
    })


@mcp.tool()
async def delete_investment_account(account_id: int) -> Any:
    """Delete an investment account and ALL its transactions. DESTRUCTIVE: only call
    after explicit user confirmation of the specific account."""
    return await backend.delete(f"/investments/accounts/{account_id}")


@mcp.tool()
async def create_investment_transaction(account_id: int, type: str, amount: float,
                                        asset_account_id: Optional[int] = None,
                                        profit: Optional[float] = None,
                                        description: Optional[str] = None,
                                        date: Optional[str] = None) -> Any:
    """Record an investment transaction. `type` is 'INVEST' (deducts from asset
    account) or 'WITHDRAW' (adds amount + profit to asset account). Pass
    `asset_account_id` to sync the money movement. `date` defaults to now."""
    return await backend.post("/investments/transactions", json=_clean({
        "account_id": account_id,
        "type": type,
        "amount": amount,
        "asset_account_id": asset_account_id,
        "profit": profit,
        "description": description,
        "date": date or now_iso(),
    }))


@mcp.tool()
async def list_investment_transactions() -> Any:
    """List all investment transactions (most recent first)."""
    return await backend.get("/investments/transactions")


@mcp.tool()
async def update_investment_transaction(transaction_id: int, account_id: int, type: str,
                                        amount: float, asset_account_id: Optional[int] = None,
                                        profit: Optional[float] = None,
                                        description: Optional[str] = None,
                                        date: Optional[str] = None) -> Any:
    """Update an investment transaction (balances are re-synced). Only call after the
    user clearly identifies the transaction; otherwise confirm first. `date` defaults to now."""
    return await backend.put(f"/investments/transactions/{transaction_id}", json=_clean({
        "account_id": account_id,
        "type": type,
        "amount": amount,
        "asset_account_id": asset_account_id,
        "profit": profit,
        "description": description,
        "date": date or now_iso(),
    }))


@mcp.tool()
async def delete_investment_transaction(transaction_id: int) -> Any:
    """Delete an investment transaction and reverse its balance effects. DESTRUCTIVE:
    only call after explicit user confirmation of the specific transaction."""
    return await backend.delete(f"/investments/transactions/{transaction_id}")


# ---------------------------------------------------------------------------
# Wishlist
# ---------------------------------------------------------------------------

@mcp.tool()
async def create_wishlist_item(name: str, estimated_amount: float, priority: str = "Medium",
                               link: Optional[str] = None, notes: Optional[str] = None) -> Any:
    """Add an item to the wishlist. `priority` is 'High', 'Medium', or 'Low'."""
    return await backend.post("/wishlist/", json=_clean({
        "name": name, "estimated_amount": estimated_amount, "priority": priority,
        "link": link, "notes": notes,
    }))


@mcp.tool()
async def list_wishlist_items() -> Any:
    """List all wishlist items (most recent first) with status and priority."""
    return await backend.get("/wishlist/")


@mcp.tool()
async def update_wishlist_item(item_id: int, name: str, estimated_amount: float,
                               priority: str, status: str, link: Optional[str] = None,
                               notes: Optional[str] = None) -> Any:
    """Update a wishlist item. `status` is 'PENDING' or 'BOUGHT'. Confirm first unless
    the item is unambiguous."""
    return await backend.put(f"/wishlist/{item_id}", json=_clean({
        "name": name, "estimated_amount": estimated_amount, "priority": priority,
        "status": status, "link": link, "notes": notes,
    }))


@mcp.tool()
async def delete_wishlist_item(item_id: int) -> Any:
    """Delete a wishlist item. DESTRUCTIVE: only call after explicit user confirmation
    of the specific item."""
    return await backend.delete(f"/wishlist/{item_id}")


@mcp.tool()
async def buy_wishlist_item(item_id: int, account_id: int, amount: float,
                            date: Optional[str] = None) -> Any:
    """Mark a wishlist item as bought: creates an expense and deducts from the account.
    SPENDS MONEY: confirm with the user if the account or amount is missing or unclear.
    `date` defaults to now."""
    return await backend.post(f"/wishlist/{item_id}/buy", json={
        "account_id": account_id,
        "amount": amount,
        "date": date or now_iso(),
    })


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
