from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select, func, delete
from typing import List, Dict, Any, Optional
from datetime import datetime
from database import get_session
from models import LoanAccount, LoanTransaction

router = APIRouter(
    prefix="/loans",
    tags=["loans"],
)

# --- Loan Accounts ---

@router.post("/accounts", response_model=LoanAccount)
def create_loan_account(account: LoanAccount, session: Session = Depends(get_session)):
    session.add(account)
    session.commit()
    session.refresh(account)
    return account

@router.get("/accounts", response_model=List[LoanAccount])
def get_loan_accounts(session: Session = Depends(get_session)):
    return session.exec(select(LoanAccount).order_by(LoanAccount.created_at.desc())).all()

@router.put("/accounts/{account_id}", response_model=LoanAccount)
def update_loan_account(account_id: int, account_data: LoanAccount, session: Session = Depends(get_session)):
    account = session.get(LoanAccount, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    account.name = account_data.name
    account.type = account_data.type
    account.status = account_data.status
    
    session.add(account)
    session.commit()
    session.refresh(account)
    return account

@router.delete("/accounts/{account_id}")
def delete_loan_account(account_id: int, session: Session = Depends(get_session)):
    account = session.get(LoanAccount, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    # Delete associated transactions first
    session.exec(delete(LoanTransaction).where(LoanTransaction.loan_account_id == account_id))
    
    session.delete(account)
    session.commit()
    return {"ok": True}

# --- Loan Transactions ---

from models import LoanAccount, LoanTransaction, Account

# ... (imports remain)

@router.post("/transactions", response_model=LoanTransaction)
def create_loan_transaction(transaction: LoanTransaction, session: Session = Depends(get_session)):
    loan_account = session.get(LoanAccount, transaction.loan_account_id)
    if not loan_account:
        raise HTTPException(status_code=404, detail="Loan Account not found")

    # Update Loan Account Balance (Outstanding Amount)
    if transaction.type == "PRINCIPAL":
        loan_account.balance += transaction.amount
    elif transaction.type == "REPAYMENT":
        loan_account.balance -= transaction.amount
    
    # Auto-update status based on balance
    if abs(loan_account.balance) < 0.01:
        loan_account.status = "SETTLED"
    else:
        loan_account.status = "ACTIVE"
    
    # Handle Asset Account Balance Update (Money Movement)
    if transaction.asset_account_id:
        asset_account = session.get(Account, transaction.asset_account_id)
        if not asset_account:
             raise HTTPException(status_code=404, detail="Asset Account not found")
        
        # Logic:
        # If I LEND money (GIVEN, PRINCIPAL) -> Money leaves my Asset Account (-)
        # If I GET REPAID (GIVEN, REPAYMENT) -> Money enters my Asset Account (+)
        # If I BORROW money (TAKEN, PRINCIPAL) -> Money enters my Asset Account (+)
        # If I PAY BACK (TAKEN, REPAYMENT) -> Money leaves my Asset Account (-)
        
        is_given = loan_account.type == 'GIVEN'
        is_taken = loan_account.type == 'TAKEN'
        is_principal = transaction.type == 'PRINCIPAL'
        is_repayment = transaction.type == 'REPAYMENT'
        
        if (is_given and is_principal) or (is_taken and is_repayment):
             asset_account.balance -= transaction.amount
        elif (is_given and is_repayment) or (is_taken and is_principal):
             asset_account.balance += transaction.amount
             
        session.add(asset_account)
    
    session.add(transaction)
    session.add(loan_account)
    session.commit()
    session.refresh(transaction)
    session.refresh(loan_account) 
    return transaction

@router.get("/transactions", response_model=List[LoanTransaction])
def get_loan_transactions(
    account_id: Optional[int] = Query(None),
    session: Session = Depends(get_session)
):
    query = select(LoanTransaction)
    if account_id:
        query = query.where(LoanTransaction.loan_account_id == account_id)
    
    return session.exec(query.order_by(LoanTransaction.date.desc())).all()

@router.delete("/transactions/{transaction_id}")
def delete_loan_transaction(transaction_id: int, session: Session = Depends(get_session)):
    transaction = session.get(LoanTransaction, transaction_id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    loan_account = session.get(LoanAccount, transaction.loan_account_id)
    if loan_account:
        # Reverse loan balance update
        if transaction.type == "PRINCIPAL":
            loan_account.balance -= transaction.amount
        elif transaction.type == "REPAYMENT":
            loan_account.balance += transaction.amount
        session.add(loan_account)

    # Reverse Asset Account Balance Update
    if transaction.asset_account_id:
        asset_account = session.get(Account, transaction.asset_account_id)
        if asset_account and loan_account:
            is_given = loan_account.type == 'GIVEN'
            is_taken = loan_account.type == 'TAKEN'
            is_principal = transaction.type == 'PRINCIPAL'
            is_repayment = transaction.type == 'REPAYMENT'
            
            # Logic (Inverted from Create):
            # Originally deducted? Now Add back.
            # Originally added? Now Deduct.
            
            if (is_given and is_principal) or (is_taken and is_repayment):
                 asset_account.balance += transaction.amount
            elif (is_given and is_repayment) or (is_taken and is_principal):
                 asset_account.balance -= transaction.amount
            
            session.add(asset_account)

    session.delete(transaction)
    session.commit()
    return {"ok": True}

# --- Dashboard Stats ---

@router.get("/dashboard", response_model=Dict[str, float])
def get_loan_stats(session: Session = Depends(get_session)):
    accounts = session.exec(select(LoanAccount).where(LoanAccount.status == "ACTIVE")).all()
    
    total_given = sum(a.balance for a in accounts if a.type == "GIVEN")
    total_taken = sum(a.balance for a in accounts if a.type == "TAKEN")
    net_position = total_given - total_taken
    
    return {
        "total_given": total_given,
        "total_taken": total_taken,
        "net_position": net_position
    }
