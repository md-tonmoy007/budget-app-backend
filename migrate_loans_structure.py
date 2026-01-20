from sqlmodel import Session, select, SQLModel
from database import engine
from models import Loan, LoanAccount, LoanTransaction
from datetime import datetime

def migrate():
    with Session(engine) as session:
        # Create tables for new models if they don't exist
        SQLModel.metadata.create_all(engine)
        
        # Get all existing loans
        loans = session.exec(select(Loan)).all()
        
        print(f"Found {len(loans)} old loan entries to migrate.")
        
        # Group by person_name and type to create accounts
        # keys: (person_name, type) -> LoanAccount
        accounts_map = {}
        
        for loan in loans:
            key = (loan.person_name, loan.type)
            
            if key not in accounts_map:
                # Create new account
                print(f"Creating account for {loan.person_name} ({loan.type})")
                account = LoanAccount(
                    name=loan.person_name,
                    type=loan.type,
                    balance=0.0, # Will calculate
                    status="ACTIVE",
                    created_at=loan.date # Use first loan date as creation? Or now? Let's use loan date if it's the earliest, but for now just use loan.date for simplicity
                )
                session.add(account)
                session.commit()
                session.refresh(account)
                accounts_map[key] = account
            
            account = accounts_map[key]
            
            # Create transaction (Initially all old loans are PRINCIPAL amounts)
            # wait, if it's a loan, `amount` is the principal.
            # We treat all existing simple loans as "Principle" transactions.
            print(f"  - Migrating loan id {loan.id}: {loan.amount}")
            
            vocab_type = "PRINCIPAL"
            
            transaction = LoanTransaction(
                loan_account_id=account.id,
                date=loan.date,
                type=vocab_type,
                amount=loan.amount,
                description=loan.description or "Migrated from legacy loan"
            )
            session.add(transaction)
            
            # Update balance
            # For GIVEN: Principal adds to balance (money owed to me)
            # For TAKEN: Principal adds to balance (money I owe)
            # So in both cases, Principal increases the "Loan Balance"
            account.balance += loan.amount
            
            session.add(account)
            
        session.commit()
        print("Migration complete.")

if __name__ == "__main__":
    migrate()
