from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select, func
from typing import List, Dict, Any
from datetime import datetime
from database import get_session
from models import Expense, Account

router = APIRouter(
    prefix="/expenses",
    tags=["expenses"],
)

def parse_numeric(value: Any) -> float:
    if isinstance(value, str):
        # Remove commas, currency symbols, and extra spaces
        clean_value = value.replace(',', '').replace('$', '').replace('€', '').replace('£', '').strip()
        try:
            return float(clean_value)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid numeric value: {value}")
    try:
        return float(value)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail=f"Could not convert {value} to number")

def parse_int(value: Any) -> int:
    if value is None:
        return None
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid integer value: {value}")
    try:
        return int(value)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail=f"Could not convert {value} to integer")

@router.post("/", response_model=Expense)
def create_expense(expense_input: Dict[str, Any], session: Session = Depends(get_session)):
    # Convert types for robustness
    if "amount" in expense_input:
        expense_input["amount"] = parse_numeric(expense_input["amount"])
    if "account_id" in expense_input:
        expense_input["account_id"] = parse_int(expense_input["account_id"])
    
    # Create Expense object (SQLModel will handle datetime conversion from string)
    try:
        expense = Expense(**expense_input)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid expense data: {str(e)}")

    # Verify account exists if provided
    if expense.account_id:
        account = session.get(Account, expense.account_id)
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        # Deduct amount from account balance
        account.balance -= expense.amount
        session.add(account)
    
    session.add(expense)
    session.commit()
    session.refresh(expense)
    return expense

@router.get("/")
def read_expenses(
    skip: int = 0, 
    limit: int = 100, 
    session: Session = Depends(get_session)
):
    # Join with Account to get account name
    statement = select(Expense, Account.name).join(Account, isouter=True).offset(skip).limit(limit).order_by(Expense.datetime.desc())
    results = session.exec(statement).all()
    
    # Format response
    expenses_with_account = []
    for expense, account_name in results:
        exp_dict = expense.model_dump()
        exp_dict["account_name"] = account_name
        expenses_with_account.append(exp_dict)
        
    return expenses_with_account

@router.get("/dashboard", response_model=Dict[str, Any])
def get_dashboard_stats(session: Session = Depends(get_session)):
    now = datetime.now()
    start_of_month = datetime(now.year, now.month, 1)
    
    # Total expenses this month
    query = select(func.sum(Expense.amount)).where(Expense.datetime >= start_of_month)
    total_monthly_expense = session.exec(query).first() or 0.0
    
    # Recent expenses
    recent_expenses = session.exec(
        select(Expense).where(Expense.datetime >= start_of_month).order_by(Expense.datetime.desc()).limit(5)
    ).all()
    
    return {
        "current_month_total": total_monthly_expense,
        "recent_expenses": recent_expenses
    }

@router.put("/{expense_id}", response_model=Expense)
def update_expense(expense_id: int, expense_data: Dict[str, Any], session: Session = Depends(get_session)):
    expense = session.get(Expense, expense_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    # Pre-process numeric types
    if "amount" in expense_data:
        expense_data["amount"] = parse_numeric(expense_data["amount"])
    if "account_id" in expense_data:
        expense_data["account_id"] = parse_int(expense_data["account_id"])

    # Handle Balance Update
    old_amount = expense.amount
    old_account_id = expense.account_id
    
    # Revert old balance
    if old_account_id:
        old_account = session.get(Account, old_account_id)
        if old_account:
            old_account.balance += old_amount
            session.add(old_account)

    # Update fields
    for key, value in expense_data.items():
        if hasattr(expense, key):
            # Special handling for datetime if it's a string
            if key == "datetime" and isinstance(value, str):
                try:
                    value = datetime.fromisoformat(value.replace('Z', '+00:00'))
                except ValueError:
                    pass # Let SQLModel/Pydantic try if this fails
            setattr(expense, key, value)
    
    # Apply new balance
    if expense.account_id:
        new_account = session.get(Account, expense.account_id)
        if not new_account:
            raise HTTPException(status_code=404, detail="New Account not found")
        new_account.balance -= expense.amount
        session.add(new_account)
        
    session.add(expense)
    session.commit()
    session.refresh(expense)
    return expense

@router.delete("/{expense_id}")
def delete_expense(expense_id: int, session: Session = Depends(get_session)):
    expense = session.get(Expense, expense_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    # Refund balance to account
    if expense.account_id:
        account = session.get(Account, expense.account_id)
        if account:
            account.balance += expense.amount
            session.add(account)
            
    session.delete(expense)
    session.commit()
    return {"ok": True}
