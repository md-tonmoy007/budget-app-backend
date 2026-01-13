from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select, func
from typing import List, Dict, Any
from datetime import datetime
from database import get_session
from models import Loan

router = APIRouter(
    prefix="/loans",
    tags=["loans"],
)

@router.post("/", response_model=Loan)
def create_loan(loan: Loan, session: Session = Depends(get_session)):
    session.add(loan)
    session.commit()
    session.refresh(loan)
    return loan

@router.get("/", response_model=List[Loan])
def read_loans(session: Session = Depends(get_session)):
    loans = session.exec(select(Loan).order_by(Loan.date.desc())).all()
    return loans

@router.get("/dashboard", response_model=Dict[str, float])
def get_loan_stats(session: Session = Depends(get_session)):
    loans = session.exec(select(Loan)).all()
    
    total_given = sum(l.amount for l in loans if l.type == "GIVEN")
    total_taken = sum(l.amount for l in loans if l.type == "TAKEN")
    net_position = total_given - total_taken
    
    return {
        "total_given": total_given,
        "total_taken": total_taken,
        "net_position": net_position
    }

@router.put("/{loan_id}", response_model=Loan)
def update_loan(loan_id: int, loan_data: Loan, session: Session = Depends(get_session)):
    loan = session.get(Loan, loan_id)
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")
    
    collection_data = loan_data.model_dump(exclude_unset=True)
    for key, value in collection_data.items():
        setattr(loan, key, value)
        
    session.add(loan)
    session.commit()
    session.refresh(loan)
    return loan

@router.delete("/{loan_id}")
def delete_loan(loan_id: int, session: Session = Depends(get_session)):
    loan = session.get(Loan, loan_id)
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")
    session.delete(loan)
    session.commit()
    return {"ok": True}
