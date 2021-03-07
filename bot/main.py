import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.utils.exceptions import TelegramAPIError
from aiogram.types import BotCommand
from aiogram.contrib.fsm_storage.memory import MemoryStorage

from bot.api.redis_sub import RedisListener
from bot.core import cfg
from bot.core.logging import setup_logging
from bot.core.middlewares import AccessMiddleware
from bot.telegram.handlers.notify import register_handlers_notify

setup_logging()
logger = logging.getLogger(__name__)


async def set_commands(tg_bot: Bot):
    commands = [
        BotCommand(command="/notify", description="Поставить уведомление об изменении цены акции")
    ]
    await tg_bot.set_my_commands(commands)


async def main():
    bot = Bot(token=cfg.get("TELEGRAM_API_TOKEN"))
    dp = Dispatcher(bot, storage=MemoryStorage())

    dp.middleware.setup(LoggingMiddleware())
    dp.middleware.setup(AccessMiddleware(cfg.get("TELEGRAM_ACCESS_ID")))

    register_handlers_notify(dp)

    await set_commands(bot)

    notify_listener = RedisListener()

    try:
        await asyncio.gather(dp.start_polling(), notify_listener.start(bot=bot, queue=cfg.get('REDIS_NOTIFICATION_QUEUE')))
    finally:
        await dp.storage.close()
        await dp.storage.wait_closed()
        await bot.close()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info(f'Buy!')
    except TelegramAPIError as err:
        logging.error(f'Handling error: {err.args}')
