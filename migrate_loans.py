from sqlmodel import SQLModel
from database import engine
from models import Loan

def migrate():
    print("Creating tables...")
    SQLModel.metadata.create_all(engine)
    print("Migration successful: 'loan' table created.")

if __name__ == "__main__":
    migrate()
