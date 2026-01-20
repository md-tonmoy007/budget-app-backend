from typing import Optional
from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship

class Account(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    type: str # e.g., 'Cash', 'Bank', 'Credit Card'
    balance: float = Field(default=0.0)

class Expense(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    datetime: datetime
    expense_type: str # e.g., 'Food', 'Transport'
    amount: float
    description: Optional[str] = None
    account_id: Optional[int] = Field(default=None, foreign_key="account.id")

class Income(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    datetime: datetime
    income_type: str # e.g., 'Salary', 'Freelance', 'Investment'
    amount: float
    description: Optional[str] = None
    account_id: Optional[int] = Field(default=None, foreign_key="account.id")

class Loan(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    person_name: str = Field(index=True)
    type: str # 'GIVEN' or 'TAKEN'
    amount: float
    date: datetime
    description: Optional[str] = None

class LoanAccount(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True) # Person or Institution Name
    type: str # 'GIVEN' (I lent money) or 'TAKEN' (I borrowed money)
    balance: float = Field(default=0.0) # Current outstanding balance
    status: str = Field(default="ACTIVE") # 'ACTIVE', 'SETTLED'
    created_at: datetime = Field(default_factory=datetime.now)

class LoanTransaction(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    loan_account_id: int = Field(foreign_key="loanaccount.id")
    asset_account_id: Optional[int] = Field(default=None, foreign_key="account.id") # Link to Asset Account (Cash/Bank)
    date: datetime
    type: str # 'PRINCIPAL' (Lending/Borrowing more), 'REPAYMENT' (Paying back)
    amount: float
    description: Optional[str] = None

class InvestmentAccount(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    company_name: str
    agent_name: str
    status: str = Field(default="ACTIVE") # 'ACTIVE', 'CLOSED'
    created_at: datetime = Field(default_factory=datetime.now)

class InvestmentTransaction(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    account_id: int = Field(foreign_key="investmentaccount.id")
    asset_account_id: Optional[int] = Field(default=None, foreign_key="account.id") # Link to Asset Account (Cash/Bank)
    date: datetime
    type: str # 'INVEST', 'WITHDRAW'
    amount: float
    profit: Optional[float] = None
    description: Optional[str] = None

class WishlistItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    estimated_amount: float
    priority: str = Field(default="Medium") # High, Medium, Low
    status: str = Field(default="PENDING") # PENDING, BOUGHT
    link: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
