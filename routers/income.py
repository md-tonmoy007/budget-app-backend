from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select, func
from typing import List, Dict, Any
from datetime import datetime
from database import get_session
from models import Income, Account

router = APIRouter(
    prefix="/income",
    tags=["income"],
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

@router.post("/", response_model=Income)
def create_income(income_input: Dict[str, Any], session: Session = Depends(get_session)):
    # Convert types for robustness
    if "amount" in income_input:
        income_input["amount"] = parse_numeric(income_input["amount"])
    if "account_id" in income_input:
        income_input["account_id"] = parse_int(income_input["account_id"])
    
    # Create Income object (SQLModel will handle datetime conversion from string)
    try:
        income = Income(**income_input)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid income data: {str(e)}")

    # Verify account exists if provided
    if income.account_id:
        account = session.get(Account, income.account_id)
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        # Add amount to account balance (key difference from expenses)
        account.balance += income.amount
        session.add(account)
    
    session.add(income)
    session.commit()
    session.refresh(income)
    return income

@router.get("/")
def read_income(
    skip: int = 0, 
    limit: int = 100, 
    session: Session = Depends(get_session)
):
    # Join with Account to get account name
    statement = select(Income, Account.name).join(Account, isouter=True).offset(skip).limit(limit).order_by(Income.datetime.desc())
    results = session.exec(statement).all()
    
    # Format response
    income_with_account = []
    for income, account_name in results:
        inc_dict = income.model_dump()
        inc_dict["account_name"] = account_name
        income_with_account.append(inc_dict)
        
    return income_with_account

@router.get("/dashboard", response_model=Dict[str, Any])
def get_dashboard_stats(session: Session = Depends(get_session)):
    now = datetime.now()
    start_of_month = datetime(now.year, now.month, 1)
    
    # Total income this month
    query = select(func.sum(Income.amount)).where(Income.datetime >= start_of_month)
    total_monthly_income = session.exec(query).first() or 0.0
    
    # Recent income
    recent_income = session.exec(
        select(Income).where(Income.datetime >= start_of_month).order_by(Income.datetime.desc()).limit(5)
    ).all()
    
    return {
        "current_month_total": total_monthly_income,
        "recent_income": recent_income
    }

@router.put("/{income_id}", response_model=Income)
def update_income(income_id: int, income_data: Dict[str, Any], session: Session = Depends(get_session)):
    income = session.get(Income, income_id)
    if not income:
        raise HTTPException(status_code=404, detail="Income not found")
    
    # Pre-process numeric types
    if "amount" in income_data:
        income_data["amount"] = parse_numeric(income_data["amount"])
    if "account_id" in income_data:
        income_data["account_id"] = parse_int(income_data["account_id"])

    # Handle Balance Update
    old_amount = income.amount
    old_account_id = income.account_id
    
    # Revert old balance (subtract the income that was added)
    if old_account_id:
        old_account = session.get(Account, old_account_id)
        if old_account:
            old_account.balance -= old_amount
            session.add(old_account)

    # Update fields
    for key, value in income_data.items():
        if hasattr(income, key):
            # Special handling for datetime if it's a string
            if key == "datetime" and isinstance(value, str):
                try:
                    value = datetime.fromisoformat(value.replace('Z', '+00:00'))
                except ValueError:
                    pass # Let SQLModel/Pydantic try if this fails
            setattr(income, key, value)
    
    # Apply new balance (add the new income amount)
    if income.account_id:
        new_account = session.get(Account, income.account_id)
        if not new_account:
            raise HTTPException(status_code=404, detail="New Account not found")
        new_account.balance += income.amount
        session.add(new_account)
        
    session.add(income)
    session.commit()
    session.refresh(income)
    return income

@router.delete("/{income_id}")
def delete_income(income_id: int, session: Session = Depends(get_session)):
    income = session.get(Income, income_id)
    if not income:
        raise HTTPException(status_code=404, detail="Income not found")
    
    # Remove income from account balance (subtract since we're reversing the addition)
    if income.account_id:
        account = session.get(Account, income.account_id)
        if account:
            account.balance -= income.amount
            session.add(account)
            
    session.delete(income)
    session.commit()
    return {"ok": True}
