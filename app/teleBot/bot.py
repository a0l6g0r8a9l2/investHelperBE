import logging

from aiogram import Bot

from app.core.config import load_config
from app.core.logging import setup_logging

# сетап конфиг и логгер
setup_logging()
logger = logging.getLogger(__name__)

API_TOKEN = load_config().get("token")


async def send_message_to_telegram(msg: str, chat_id: str = 411442889):
    # Initialize bot
    bot = Bot(token=API_TOKEN)
    await bot.send_message(chat_id=chat_id, text=msg)
    await bot.close()
