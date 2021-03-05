import logging

import aioredis
from aioredis import ConnectionForcedCloseError

from app.core import config_data
from app.core.logging import setup_logging
from app.models.models import NotificationMessage

setup_logging()
logger = logging.getLogger(__name__)


class RedisPublisher:
    def __init__(self, host: str = config_data.get("REDIS_HOST"), port: int = config_data.get("REDIS_PORT")):
        self.redis_connection_string = f'redis://{host}:{port}/0'

    async def start(self, message: NotificationMessage, queue: str = 'notification:stock:price:received'):
        redis = await aioredis.create_redis(self.redis_connection_string, encoding='utf-8')
        try:
            redis.rpush(queue, message)
            logging.debug(f'Message pushed to redis queue: {queue}')
            redis.close()
        except Exception as err:
            logging.error(err.args)
        except ConnectionForcedCloseError as err:
            logging.warning(f'{err.args}')
        finally:
            await redis.wait_closed()
