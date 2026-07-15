import logging
from telegram import Update
from telegram.ext import ContextTypes
from ..ai.agent import FinanceAssistant

logger = logging.getLogger(__name__)

agent: FinanceAssistant | None = None


def get_agent() -> FinanceAssistant:
    global agent
    if agent is None:
        agent = FinanceAssistant()
    return agent

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle incoming text messages by passing them to the AI agent.
    """
    user_message = update.message.text
    chat_id = update.effective_chat.id
    user = update.effective_user
    logger.info(
        "Incoming message from chat_id=%s user=%s (%s): %r",
        chat_id,
        getattr(user, "username", None) or getattr(user, "id", None),
        getattr(user, "full_name", None),
        user_message,
    )

    # Send a typing action to indicate processing
    await update.message.chat.send_action(action="typing")

    try:
        # Process message with AI Agent (per-chat id enables multi-turn confirmations)
        response = await get_agent().process_message(chat_id, user_message)

        # Reply to user
        logger.info("Reply to chat_id=%s: %r", chat_id, response)
        await update.message.reply_text(response)

    except Exception as e:
        logger.error(f"Error handling message: {e}", exc_info=True)
        await update.message.reply_text("Sorry, I encountered an error processing that request.")
