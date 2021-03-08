import json
import logging
from typing import Optional

import aioredis
from aiogram import Bot
from aiogram.utils.exceptions import TelegramAPIError
from aioredis import RedisError
from pydantic import ValidationError

from bot.core import cfg
from bot.core.logging import setup_logging
from bot.models.models import NotificationMessage
from bot.telegram.utils import MarkdownMessageBuilder

setup_logging()
logger = logging.getLogger(__name__)


class RedisListener:
    def __init__(self, host: str = cfg.get("REDIS_HOST"), port: str = cfg.get("REDIS_PORT")):
        self.redis_connection_string = f'redis://{host}:{port}/0'

    async def start(self, bot: Bot, queue: str = 'notification:stock:price:received'):
        try:
            redis = await aioredis.create_redis(self.redis_connection_string, encoding='utf-8')
            while True:
                row_message = await redis.blpop(queue)
                logging.debug(f'Message received {json.loads(row_message[1])}')
                typed_message = self.validate_message(message=json.loads(row_message[1]))
                message_text = MarkdownMessageBuilder(row_message=typed_message).build()
                if message_text:
                    await bot.send_message(chat_id=typed_message.chatId, text=message_text, parse_mode='Markdown')
        except RedisError as redis_err:
            logging.error(f'Redis error: {redis_err.args}')
        except TelegramAPIError as tg_err:
            logging.error(f'Aiogram error: {tg_err.args}')

    @classmethod
    def validate_message(cls, message) -> Optional[NotificationMessage]:
        try:
            logging.debug(f'Got message. Type: {type(message)}, content: {message}')
            message = NotificationMessage(**message)
            return message
        except ValidationError as err:
            logging.error(f'Validation message error: {err.args}')
        except Exception as err:
            logging.error(f'Unexpected error: {err.args}')
