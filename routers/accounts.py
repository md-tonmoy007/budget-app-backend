from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List
from database import get_session
from models import Account

router = APIRouter(
    prefix="/accounts",
    tags=["accounts"],
)

@router.post("/", response_model=Account)
def create_account(account: Account, session: Session = Depends(get_session)):
    session.add(account)
    session.commit()
    session.refresh(account)
    return account

@router.get("/", response_model=List[Account])
def read_accounts(session: Session = Depends(get_session)):
    accounts = session.exec(select(Account)).all()
    return accounts

    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return account

@router.put("/{account_id}", response_model=Account)
def update_account(account_id: int, account_data: Account, session: Session = Depends(get_session)):
    account = session.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    account_data_dict = account_data.model_dump(exclude_unset=True)
    for key, value in account_data_dict.items():
        setattr(account, key, value)
    
    session.add(account)
    session.commit()
    session.refresh(account)
    return account

@router.delete("/{account_id}")
def delete_account(account_id: int, session: Session = Depends(get_session)):
    account = session.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    session.delete(account)
    session.commit()
    return {"ok": True}

@router.put("/{account_id}/balance", response_model=Account)
def adjust_balance(account_id: int, amount: float, session: Session = Depends(get_session)):
    account = session.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    account.balance += amount
    session.add(account)
    session.commit()
    session.refresh(account)
    return account

from pydantic import BaseModel

class TransferRequest(BaseModel):
    from_account_id: int
    to_account_id: int
    amount: float
    description: str | None = None

@router.post("/transfer")
def transfer_funds(req: TransferRequest, session: Session = Depends(get_session)):
    from_acc = session.get(Account, req.from_account_id)
    to_acc = session.get(Account, req.to_account_id)
    
    if not from_acc:
        raise HTTPException(status_code=404, detail="Source account not found")
    if not to_acc:
        raise HTTPException(status_code=404, detail="Destination account not found")
    
    if from_acc.balance < req.amount:
        raise HTTPException(status_code=400, detail="Insufficient funds in source account")
        
    from_acc.balance -= req.amount
    to_acc.balance += req.amount
    
    session.add(from_acc)
    session.add(to_acc)
    session.commit()
    
    return {"ok": True, "new_src_balance": from_acc.balance, "new_dest_balance": to_acc.balance}
