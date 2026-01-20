from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select, delete
from typing import List
from database import get_session
from models import InvestmentAccount, InvestmentTransaction, Account
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
    # Sync with Account balance if asset_account_id is provided
    if transaction.asset_account_id:
        account = session.get(Account, transaction.asset_account_id)
        if not account:
            raise HTTPException(status_code=404, detail="Asset account not found")
        
        if transaction.type == "INVEST":
            account.balance -= transaction.amount
        elif transaction.type == "WITHDRAW":
            # Profit is also added to the account if it exists
            total_return = transaction.amount + (transaction.profit or 0)
            account.balance += total_return
        
        session.add(account)

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
    
    # Reverse balance sync if asset_account_id exists
    if transaction.asset_account_id:
        account = session.get(Account, transaction.asset_account_id)
        if account:
            if transaction.type == "INVEST":
                account.balance += transaction.amount
            elif transaction.type == "WITHDRAW":
                total_return = transaction.amount + (transaction.profit or 0)
                account.balance -= total_return
            session.add(account)

    session.delete(transaction)
    session.commit()
    return {"ok": True}
