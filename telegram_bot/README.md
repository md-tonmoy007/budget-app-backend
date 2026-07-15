# Telegram Budget Bot

This is a Telegram bot for interacting with the Budget Planner API using natural language.

## Setup

1. **Install Dependencies**
   ```bash
   cd backend
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements-dev.txt
   ```

2. **Environment Configuration**
   Copy the centralized backend env example and fill in your details:
   ```bash
   cp .env.example .env
   ```
   You need:
   - `TELEGRAM_BOT_TOKEN`: From BotFather
   - `OPENROUTER_API_KEY`: For AI capabilities
   - `OPENROUTER_MODEL`: A model with tool/function-calling support
   - `BUDGET_API_BASE_URL`: URL of your running backend (e.g., http://localhost:8000)
   - `MCP_SERVER_URL`: Streamable HTTP endpoint for the Budget Planner MCP server

3. **Run the Bot**
   Ensure your Budget Planner backend is running.
   ```bash
   python -m telegram_bot.src.bot.main
   ```

4. **Run Tests**
   ```bash
   python -m pytest
   ```

## Features
- **Natural Language Parsing**: "Spent $20 on food"
- **Expense Tracking**: Log expenses automatically
- **Income Tracking**: Record income
- **Stats**: View monthly summaries via /stats
- **Account Management**: List accounts via /accounts

## Structure
- `telegram_bot/src/bot`: Telegram bot logic (handlers, commands)
- `telegram_bot/src/ai`: AI agent logic (LangChain, prompts)
- `telegram_bot/src/api`: Client for the Budget Planner API
