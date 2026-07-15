import requests
from typing import List, Dict, Any, Optional
from ..config.config import Config
from .models import Account, Expense, Income, LoanTransaction, InvestmentTransaction, WishlistItem

class BudgetPlannerAPI:
    def __init__(self, base_url: str = None):
        self.base_url = base_url or Config.BUDGET_API_BASE_URL

    def _get(self, endpoint: str, params: Dict = None) -> Any:
        response = requests.get(f"{self.base_url}{endpoint}", params=params)
        response.raise_for_status()
        return response.json()

    def _post(self, endpoint: str, data: Dict) -> Any:
        response = requests.post(f"{self.base_url}{endpoint}", json=data)
        response.raise_for_status()
        return response.json()

    def get_accounts(self) -> List[Account]:
        data = self._get("/accounts")
        return [Account(**item) for item in data]

    def create_expense(self, expense_data: Dict) -> Expense:
        data = self._post("/expenses", expense_data)
        return Expense(**data)

    def create_income(self, income_data: Dict) -> Income:
        data = self._post("/income", income_data)
        return Income(**data)

    def create_loan_transaction(self, transaction_data: Dict) -> LoanTransaction:
        data = self._post("/loans/transactions", transaction_data)
        return LoanTransaction(**data)

    def create_investment_transaction(self, transaction_data: Dict) -> InvestmentTransaction:
        data = self._post("/investments/transactions", transaction_data)
        return InvestmentTransaction(**data)

    def create_wishlist_item(self, item_data: Dict) -> WishlistItem:
        data = self._post("/wishlist", item_data)
        return WishlistItem(**data)
    
    def get_expenses_dashboard(self) -> Dict:
        return self._get("/expenses/dashboard")
        
    def get_income_dashboard(self) -> Dict:
        return self._get("/income/dashboard")
