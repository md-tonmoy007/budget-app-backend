import logging
from telegram.error import Conflict, InvalidToken
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from ..config.config import Config
from ..config.logging import setup_logging
from .commands import start_command, help_command, stats_command, accounts_command


async def error_handler(update, context):
    logger = logging.getLogger(__name__)
    error = context.error
    if isinstance(error, Conflict):
        logger.error(
            "Telegram polling conflict: another process is already running this bot token. "
            "Stop the other local/Render bot instance, then start this one again."
        )
        context.application.stop_running()
        return

    logger.exception("Unhandled Telegram bot error", exc_info=error)


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
    application.add_error_handler(error_handler)

    logger.info("Bot started polling...")
    try:
        application.run_polling(drop_pending_updates=True)
    except InvalidToken as e:
        logger.error("Configuration Error: TELEGRAM_BOT_TOKEN was rejected by Telegram")
        raise SystemExit(1) from e
    except Conflict as e:
        logger.error(
            "Telegram polling conflict: another process is already running this bot token. "
            "Stop the duplicate instance, then start this one again."
        )
        raise SystemExit(1) from e

if __name__ == '__main__':
    main()
