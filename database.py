from sqlmodel import SQLModel, create_engine, Session
import os
from dotenv import load_dotenv

load_dotenv()

# Use the provided connection string or fallback to env var
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres.tnwxjuysfufulygykucg:jif%40t%27sfinance@aws-1-ap-northeast-2.pooler.supabase.com:6543/postgres")

engine = create_engine(DATABASE_URL, echo=True)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
