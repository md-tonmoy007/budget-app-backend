from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List, Optional
from datetime import datetime
from database import get_session
from models import WishlistItem, Expense, Account
from pydantic import BaseModel

class WishlistPurchase(BaseModel):
    account_id: int
    amount: float
    date: datetime

router = APIRouter(prefix="/wishlist", tags=["wishlist"])

@router.post("/", response_model=WishlistItem)
def create_item(item: WishlistItem, session: Session = Depends(get_session)):
    session.add(item)
    session.commit()
    session.refresh(item)
    return item

@router.get("/", response_model=List[WishlistItem])
def get_items(session: Session = Depends(get_session)):
    return session.exec(select(WishlistItem).order_by(WishlistItem.created_at.desc())).all()

@router.put("/{item_id}", response_model=WishlistItem)
def update_item(item_id: int, item_data: WishlistItem, session: Session = Depends(get_session)):
    item = session.get(WishlistItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    item.name = item_data.name
    item.estimated_amount = item_data.estimated_amount
    item.priority = item_data.priority
    item.link = item_data.link
    item.notes = item_data.notes
    item.status = item_data.status
    
    session.add(item)
    session.commit()
    session.refresh(item)
    return item

@router.delete("/{item_id}")
def delete_item(item_id: int, session: Session = Depends(get_session)):
    item = session.get(WishlistItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    session.delete(item)
    session.commit()
    return {"ok": True}

@router.post("/{item_id}/buy")
def buy_item(item_id: int, purchase: WishlistPurchase, session: Session = Depends(get_session)):
    item = session.get(WishlistItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    if item.status == "BOUGHT":
        raise HTTPException(status_code=400, detail="Item already bought")

    account = session.get(Account, purchase.account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    # 1. Update Wishlist status
    item.status = "BOUGHT"
    session.add(item)

    # 2. Create Expense
    expense = Expense(
        datetime=purchase.date,
        expense_type="Wishlist Purchase",
        amount=purchase.amount,
        description=f"Bought from Wishlist: {item.name}",
        account_id=purchase.account_id
    )
    session.add(expense)

    # 3. Deduct from Account
    account.balance -= purchase.amount
    session.add(account)

    session.commit()
    session.refresh(item)
    return {"ok": True, "item": item, "expense_id": expense.id}
