from sqlalchemy import text
from database import engine

def migrate():
    print("Starting migration: Adding 'asset_account_id' to 'investmenttransaction'...")
    try:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE investmenttransaction ADD COLUMN IF NOT EXISTS asset_account_id INTEGER;"))
            # Ensure profit column exists too just in case
            conn.execute(text("ALTER TABLE investmenttransaction ADD COLUMN IF NOT EXISTS profit FLOAT DEFAULT 0.0;"))
            conn.commit()
        print("Migration successful.")
    except Exception as e:
        print(f"Migration failed: {e}")

if __name__ == "__main__":
    migrate()
