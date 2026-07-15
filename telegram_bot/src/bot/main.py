import logging
from telegram.error import InvalidToken
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from ..config.config import Config
from ..config.logging import setup_logging
from .commands import start_command, help_command, stats_command, accounts_command

def main():
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Validate config
    try:
        Config.validate()
    except ValueError as e:
        logger.error(f"Configuration Error: {e}")
        raise SystemExit(1) from e

    from .handlers import handle_message

    # Build Application
    application = ApplicationBuilder().token(Config.TELEGRAM_BOT_TOKEN).build()

    # Register Command Handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("accounts", accounts_command))

    # Register Message Handler (for natural language)
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    logger.info("Bot started polling...")
    try:
        application.run_polling()
    except InvalidToken as e:
        logger.error("Configuration Error: TELEGRAM_BOT_TOKEN was rejected by Telegram")
        raise SystemExit(1) from e

if __name__ == '__main__':
    main()
