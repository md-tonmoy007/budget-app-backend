from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select, delete
from typing import List
from database import get_session
from models import InvestmentAccount, InvestmentTransaction
from datetime import datetime

router = APIRouter(prefix="/investments", tags=["investments"])



# --- Investment Accounts ---

@router.post("/accounts", response_model=InvestmentAccount)
def create_investment_account(account: InvestmentAccount, session: Session = Depends(get_session)):
    session.add(account)
    session.commit()
    session.refresh(account)
    return account

@router.get("/accounts", response_model=List[InvestmentAccount])
def get_investment_accounts(session: Session = Depends(get_session)):
    return session.exec(select(InvestmentAccount)).all()

@router.put("/accounts/{account_id}", response_model=InvestmentAccount)
def update_investment_account(account_id: int, account_data: InvestmentAccount, session: Session = Depends(get_session)):
    account = session.get(InvestmentAccount, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    account.company_name = account_data.company_name
    account.agent_name = account_data.agent_name
    account.status = account_data.status
    
    session.add(account)
    session.commit()
    session.refresh(account)
    return account

@router.delete("/accounts/{account_id}")
def delete_investment_account(account_id: int, session: Session = Depends(get_session)):
    account = session.get(InvestmentAccount, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    # Cascade delete transactions manually using direct delete statement
    # This prevents integrity errors by ensuring children are removed first
    session.exec(delete(InvestmentTransaction).where(InvestmentTransaction.account_id == account_id))
        
    session.delete(account)
    session.commit()
    return {"ok": True}

# --- Investment Transactions ---

@router.post("/transactions", response_model=InvestmentTransaction)
def create_investment_transaction(transaction: InvestmentTransaction, session: Session = Depends(get_session)):
    # If it's a withdrawal, we might need to update account status or calc profit
    # If the user sends a transaction with profit, we assume they calculated it or passed it.
    
    # Logic for auto-calculating profit on withdrawal could be complex if we don't have enough info.
    # The requirement says "return with investment (profit with investment money), profit".
    # We will trust the frontend/user to provide the profit amount or calculate it based on what they input.
    # However, if it's a withdrawal, we should check if we need to close the account?
    # The user request said "if i take out my money... logging that... transaction status should be changed".
    # We'll handle status change if a flag is passed, but the model doesn't have a flag in the transaction body.
    # We can handle it in the frontend closing logic or a separate endpoint, or just infer it?
    # For now, just Log.
    
    session.add(transaction)
    session.commit()
    session.refresh(transaction)
    return transaction

@router.get("/transactions", response_model=List[InvestmentTransaction])
def get_investment_transactions(session: Session = Depends(get_session)):
    return session.exec(select(InvestmentTransaction).order_by(InvestmentTransaction.date.desc())).all()

@router.delete("/transactions/{transaction_id}")
def delete_investment_transaction(transaction_id: int, session: Session = Depends(get_session)):
    transaction = session.get(InvestmentTransaction, transaction_id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    session.delete(transaction)
    session.commit()
    return {"ok": True}
