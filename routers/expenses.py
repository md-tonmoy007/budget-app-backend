from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select, func
from typing import List, Dict, Any
from datetime import datetime
from ..database import get_session
from ..models import Expense, Account

router = APIRouter(
    prefix="/expenses",
    tags=["expenses"],
)

@router.post("/", response_model=Expense)
def create_expense(expense: Expense, session: Session = Depends(get_session)):
    # Verify account exists if provided
    if expense.account_id:
        account = session.get(Account, expense.account_id)
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
    
    session.add(expense)
    session.commit()
    session.refresh(expense)
    return expense

@router.get("/", response_model=List[Expense])
def read_expenses(
    skip: int = 0, 
    limit: int = 100, 
    session: Session = Depends(get_session)
):
    expenses = session.exec(select(Expense).offset(skip).limit(limit)).all()
    return expenses

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
def update_expense(expense_id: int, expense_data: Expense, session: Session = Depends(get_session)):
    expense = session.get(Expense, expense_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    # Update balance logic? Ideally, we revert old amount and apply new. 
    # For now, let's keep it simple or user handles balance separately?
    # User asked for "ability to add or remove amounts available in that account".
    # Syncing expense with balance is complex property.
    # Let's just update the record.
    
    collection_data = expense_data.model_dump(exclude_unset=True)
    for key, value in collection_data.items():
        setattr(expense, key, value)
        
    session.add(expense)
    session.commit()
    session.refresh(expense)
    return expense

@router.delete("/{expense_id}")
def delete_expense(expense_id: int, session: Session = Depends(get_session)):
    expense = session.get(Expense, expense_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    session.delete(expense)
    session.commit()
    return {"ok": True}
