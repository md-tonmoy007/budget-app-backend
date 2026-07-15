from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

class Account(BaseModel):
    id: Optional[int] = None
    name: str
    type: str
    balance: float = 0.0

class Expense(BaseModel):
    id: Optional[int] = None
    datetime: datetime
    expense_type: str
    amount: float
    description: Optional[str] = None
    account_id: Optional[int] = None

class Income(BaseModel):
    id: Optional[int] = None
    datetime: datetime
    income_type: str
    amount: float
    description: Optional[str] = None
    account_id: Optional[int] = None

class LoanAccount(BaseModel):
    id: Optional[int] = None
    name: str
    type: str  # GIVEN or TAKEN
    balance: float = 0.0
    status: str = "ACTIVE"
    created_at: Optional[datetime] = None

class LoanTransaction(BaseModel):
    id: Optional[int] = None
    loan_account_id: int
    asset_account_id: Optional[int] = None
    date: datetime
    type: str  # PRINCIPAL or REPAYMENT
    amount: float
    description: Optional[str] = None

class InvestmentAccount(BaseModel):
    id: Optional[int] = None
    company_name: str
    agent_name: str
    status: str = "ACTIVE"
    created_at: Optional[datetime] = None

class InvestmentTransaction(BaseModel):
    id: Optional[int] = None
    account_id: int
    asset_account_id: Optional[int] = None
    date: datetime
    type: str  # INVEST or WITHDRAW
    amount: float
    profit: float = 0.0
    description: Optional[str] = None

class WishlistItem(BaseModel):
    id: Optional[int] = None
    name: str
    estimated_amount: float
    priority: str = "Medium"
    status: str = "PENDING"
    link: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None

class DashboardStats(BaseModel):
    current_month_total: float
    recent_transactions: List[dict] = []
