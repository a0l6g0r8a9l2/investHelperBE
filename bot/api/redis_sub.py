import json
import logging
from typing import Optional

import aioredis
from aiogram import Bot
from aiogram.utils.exceptions import TelegramAPIError
from aioredis import RedisError
from pydantic import ValidationError

from bot.core import settings
from bot.core.logging import setup_logging
from bot.models.models import StockPriceNotificationReadRs
from bot.telegram.utils import MarkdownMessageBuilder

setup_logging()
logger = logging.getLogger(__name__)


class RedisListener:
    def __init__(self, host: str = settings.redis_host, port: int = settings.redis_port, db: int = 0):
        self.redis_connection_string = f'redis://{host}:{port}/{db}'

    async def start(self, bot: Bot, queue: str = settings.redis_notification_queue):
        try:
            redis = await aioredis.create_redis(self.redis_connection_string, encoding='utf-8')
            while True:
                row_message = await redis.blpop(queue)
                logging.debug(f'Message received {json.loads(row_message[1])}')
                typed_message = self.validate_message(message=json.loads(row_message[1]))
                message_text = MarkdownMessageBuilder(row_message=typed_message).build_notification_message()
                if message_text:
                    await bot.send_message(chat_id=typed_message.chatId, text=message_text, parse_mode='Markdown')
        except RedisError as redis_err:
            logging.error(f'Redis error: {redis_err.args}')
        except TelegramAPIError as tg_err:
            logging.error(f'Aiogram error: {tg_err.args}')

    @classmethod
    def validate_message(cls, message) -> Optional[StockPriceNotificationReadRs]:
        try:
            logging.debug(f'Got message. Type: {type(message)}, content: {message}')
            message = StockPriceNotificationReadRs(**message)
            return message
        except ValidationError as err:
            logging.error(f'Validation message error: {err.args}')
        except Exception as err:
            logging.error(f'Unexpected error: {err.args}')
