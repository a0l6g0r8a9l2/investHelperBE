import logging

import aioredis
from aioredis import RedisError

from app.core import config_data
from app.core.logging import setup_logging
from app.models.models import NotificationMessage

setup_logging()
logger = logging.getLogger(__name__)


class Redis:
    def __init__(self, host: str = config_data.get("REDIS_HOST"), port: str = config_data.get("REDIS_PORT")):
        self.redis_connection_string = f'redis://{host}:{port}/0'

    async def start_publish(self,
                            message: NotificationMessage,
                            queue: str = config_data.get("REDIS_NOTIFICATION_QUEUE")):
        redis = await aioredis.create_redis(self.redis_connection_string, encoding='utf-8')
        try:
            redis.rpush(queue, message)
            logging.debug(f'Message pushed to redis queue: {queue}')
        except RedisError as redis_err:
            logging.error(f'Redis error: {redis_err.args}')
        finally:
            redis.close()
            await redis.wait_closed()

    async def save_cache(self,
                         message: str,
                         collection_key: str = config_data.get("REDIS_BONDS_LIST_CACHE_KEY"),
                         ttl_per_sec: int = config_data.get("REDIS_BONDS_LIST_CACHE_TTL")):
        redis = await aioredis.create_redis(self.redis_connection_string, encoding='utf-8')
        try:
            await redis.setex(key=collection_key, seconds=ttl_per_sec, value=message)
            logging.debug(f'Message saved to redis key: {collection_key}, ttl: {ttl_per_sec} sec')
            return collection_key
        except RedisError as redis_err:
            logging.error(f'Redis error: {redis_err.args}')
        finally:
            redis.close()
            await redis.wait_closed()

    async def get_cached(self,
                         collection_key: str = config_data.get("REDIS_BONDS_LIST_CACHE_KEY")):
        redis = await aioredis.create_redis(self.redis_connection_string, encoding='utf-8')
        try:
            message = await redis.get(key=collection_key, encoding='utf-8')
            logging.debug(f'Message got from redis key: {collection_key}')
            return message
        except RedisError as redis_err:
            logging.error(f'Redis error: {redis_err.args}')
        finally:
            redis.close()
            await redis.wait_closed()
