from sqlalchemy import text
from database import engine

def migrate():
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE account ADD COLUMN IF NOT EXISTS balance FLOAT DEFAULT 0.0;"))
        conn.commit()
    print("Migration successful: Added 'balance' column to 'account' table.")

if __name__ == "__main__":
    migrate()
