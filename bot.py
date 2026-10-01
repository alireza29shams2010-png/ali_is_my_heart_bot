"""Telegram bot: sends "علی ایز مای هارت ❤️" to a chat every 5 minutes.

/start -> starts the 5-minute timer for the current chat
/stop  -> stops the timer for the current chat
"""

import logging
import os
import sys

from telegram import Update
from telegram.error import Forbidden, TelegramError
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN_ENV_VAR = "TELEGRAM_BOT_TOKEN"
INTERVAL_SECONDS = 300
TIMER_MESSAGE = "علی ایز مای هارت ❤️"

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logger = logging.getLogger("ali_is_my_heart_bot")


def timer_name(chat_id: int) -> str:
    return f"heart_timer_{chat_id}"

async def send_heart_message(context: ContextTypes.DEFAULT_TYPE) -> None:
    job = context.job
    chat_id = job.chat_id
    try:
        await context.bot.send_message(chat_id=chat_id, text=TIMER_MESSAGE)
        logger.info("Sent timer message to chat %s", chat_id)
    except Forbidden:
        logger.warning("No permission to write in chat %s. Removing its timer.", chat_id)
        job.schedule_removal()
    except TelegramError as exc:
        logger.error("Failed to send message to chat %s: %s", chat_id, exc)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    message = update.effective_message
    if chat is None or message is None:
        return

    job_queue = context.job_queue
    if job_queue is None:
        logger.error("JobQueue is not available.")
        await message.reply_text("⚠️ Internal error: the scheduler is unavailable.")
        return

    name = timer_name(chat.id)
    if job_queue.get_jobs_by_name(name):
        await message.reply_text(
            "⏱ The timer is already running in this chat.\nSend /stop to stop it."
        )
        return

    try:
        job_queue.run_repeating(
            send_heart_message,
            interval=INTERVAL_SECONDS,
            first=INTERVAL_SECONDS,
            chat_id=chat.id,
            name=name,
        )
    except Exception:
        logger.exception("Could not start timer for chat %s", chat.id)
        await message.reply_text("⚠️ Could not start the timer. Please try again.")
        return

    logger.info("Timer started for chat %s", chat.id)
    await message.reply_text(
        "✅ Timer started! I will send a message every 5 minutes.\n"
        "Send /stop to stop it."
    )

async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    message = update.effective_message
    if chat is None or message is None:
        return

    job_queue = context.job_queue
    jobs = job_queue.get_jobs_by_name(timer_name(chat.id)) if job_queue else ()
    if not jobs:
        await message.reply_text("ℹ️ No timer is running in this chat.")
        return

    for job in jobs:
        job.schedule_removal()

    logger.info("Timer stopped for chat %s", chat.id)
    await message.reply_text("🛑 Timer stopped.")


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Unhandled exception while processing an update:", exc_info=context.error)


async def post_init(application: Application) -> None:
    me = await application.bot.get_me()
    logger.info("Connected to Telegram as @%s (id %s)", me.username, me.id)
    logger.info("Bot is running with polling.")

def main() -> None:
    if sys.version_info < (3, 11):
        sys.exit("Python 3.11 or newer is required.")

    token = os.environ.get(TOKEN_ENV_VAR, "").strip()
    if not token:
        logger.critical("Environment variable %s is not set.", TOKEN_ENV_VAR)
        sys.exit(1)

    logger.info("Starting bot...")
    application = Application.builder().token(token).post_init(post_init).build()

    if application.job_queue is None:
        logger.critical("JobQueue is unavailable. Check requirements.txt.")
        sys.exit(1)

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("stop", stop_command))
    application.add_error_handler(error_handler)

    try:
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,
        )
    except TelegramError as exc:
        logger.critical("Telegram error, bot stopped: %s", exc)
        sys.exit(1)
    except Exception:
        logger.exception("Fatal error, bot stopped.")
        sys.exit(1)
    finally:
        logger.info("Bot has shut down.")

if __name__ == "__main__":
    main()
