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
