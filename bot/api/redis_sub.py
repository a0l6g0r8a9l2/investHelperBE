import asyncio
import json
import logging

import aioredis

from bot.core import cfg
from bot.core.logging import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


class RedisListener:
    def __init__(self, host: str = cfg.get("REDIS_HOST"), port: int = cfg.get("REDIS_PORT")):
        self.redis_connection_string = f'redis://{host}:{port}/0'

    async def start(self, queue: str = 'notification:stock:price:received'):
        redis = await aioredis.create_redis(self.redis_connection_string, encoding='utf-8')
        while True:
            message = await redis.blpop(queue)
            # todo: add bot send message
            logging.debug(f'Message received {json.loads(message[1])}')


if __name__ == '__main__':
    listener = RedisListener(host='localhost', port=6379)
    asyncio.run(listener.start())
