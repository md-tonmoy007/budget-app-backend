from datetime import datetime, timezone

from fastapi import FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from contextlib import asynccontextmanager
from database import create_db_and_tables, engine
from routers import accounts, expenses, loans, income, investments, wishlist

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield

app = FastAPI(lifespan=lifespan, title="Expense Tracker API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(accounts.router)
app.include_router(expenses.router)
app.include_router(loans.router)
app.include_router(income.router)
app.include_router(investments.router)
app.include_router(wishlist.router)

@app.api_route("/", methods=["GET", "HEAD"])
def read_root():
    return {"message": "Expense Tracker API is running"}

@app.get("/health")
def health_check(response: Response):
    health = {
        "status": "ok",
        "service": "budget-planner-backend",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": {
            "api": "ok",
            "database": "ok",
        },
    }

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        health["status"] = "degraded"
        health["checks"]["database"] = "error"

    return health
