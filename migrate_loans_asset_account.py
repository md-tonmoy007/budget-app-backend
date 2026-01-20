from sqlmodel import Session, text
from database import engine

def migrate_schema():
    with Session(engine) as session:
        try:
            # Check if column exists to avoid error
            session.exec(text("ALTER TABLE loantransaction ADD COLUMN asset_account_id INTEGER REFERENCES account(id)"))
            session.commit()
            print("Successfully added asset_account_id column.")
        except Exception as e:
            print(f"Migration might have already run or failed: {e}")

if __name__ == "__main__":
    migrate_schema()
