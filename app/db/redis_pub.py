import logging

import aioredis
from aioredis import RedisError

from app.core import settings
from app.core.logging import setup_logging
from app.models.models import NotificationMessage

setup_logging()
logger = logging.getLogger(__name__)


class Redis:
    def __init__(self, host: str = settings.redis_host, port: str = settings.redis_port):
        self.redis_connection_string = f'redis://{host}:{port}/0'

    async def start_publish(self,
                            message: NotificationMessage,
                            queue: str = settings.redis_notification_queue):
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
                         collection_key: str = settings.redis_bonds_list_cache_key,
                         ttl_per_sec: int = settings.redis_bonds_list_cache_ttl):
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
                         collection_key: str = settings.redis_bonds_list_cache_key):
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
