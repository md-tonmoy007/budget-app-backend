from telegram import Update
from telegram.ext import ContextTypes
from ..api.client import BudgetPlannerAPI

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_html(
        f"Hi {user.mention_html()}! I'm your Budget AI Assistant.\n"
        "I can help you track expenses, income, and more.\n"
        "Try saying 'I spent $10 on lunch' or use /help to see available commands."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
*Available Commands:*
/start - Start the bot
/help - Show this help message
/stats - Show dashboard statistics
/accounts - List your accounts

*Natural Language Examples:*
- "Spent $50 on groceries"
- "Received $1000 salary"
- "Lent $20 to Mike"
    """
    await update.message.reply_markdown(help_text)

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    api = BudgetPlannerAPI()
    try:
        expenses = api.get_expenses_dashboard()
        income = api.get_income_dashboard()
        
        # Basic error handling/defaults if keys missing
        exp_total = expenses.get('current_month_total', 0.0)
        inc_total = income.get('current_month_total', 0.0)
        
        await update.message.reply_text(
            f"Month to Date:\n"
            f"Expenses: ${exp_total:.2f}\n"
            f"Income: ${inc_total:.2f}\n"
            f"Net: ${inc_total - exp_total:.2f}"
        )
    except Exception as e:
        await update.message.reply_text(f"Error fetching stats: {str(e)}")

async def accounts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    api = BudgetPlannerAPI()
    try:
        accounts = api.get_accounts()
        if not accounts:
            await update.message.reply_text("No accounts found.")
            return
            
        text = "Your Accounts:\n" + "\n".join(
            [f"- {a.name} ({a.type}): ${a.balance:.2f}" for a in accounts]
        )
        await update.message.reply_text(text)
    except Exception as e:
         await update.message.reply_text(f"Error fetching accounts: {str(e)}")
