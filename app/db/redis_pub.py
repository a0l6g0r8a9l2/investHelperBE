import asyncio
import logging
from contextlib import asynccontextmanager
from asyncio import CancelledError
from typing import Optional, List

import aioredis
from aioredis import RedisError

from app.core import settings
from app.core.logging import setup_logging
from app.models.models import NotificationMessage

setup_logging()
logger = logging.getLogger(__name__)


def error_logging_handler(func):
    async def wrapped(*args, **kwargs):
        try:
            logger.debug(f'Call "{func.__name__}" with args: {args}, kwargs: {kwargs}')
            result = await func(*args, **kwargs)
        except RedisError as redis_err:
            logging.error(f'Redis error: {redis_err.args}')
        except CancelledError:
            done, pending = await asyncio.wait(asyncio.tasks.all_tasks())
            await asyncio.gather(pending)
        else:
            logger.debug(f'Successes call "{func.__name__}" return: {result}')
            return result
    return wrapped


class Redis:
    def __init__(self, host: str = settings.redis_host, port: str = settings.redis_port):
        self.redis_connection_string = f'redis://{host}:{port}/0'

    @asynccontextmanager
    async def get_connection(self):
        conn = await aioredis.create_redis(self.redis_connection_string, encoding='utf-8')
        try:
            yield conn
        finally:
            conn.close()
            await conn.wait_closed()

    @error_logging_handler
    async def start_publish(self,
                            message: NotificationMessage,
                            queue: str = settings.redis_notification_queue):
        async with self.get_connection() as conn:
            conn.rpush(queue, message)
            logging.debug(f'Message pushed to redis queue: {queue}')

    @error_logging_handler
    async def save_cache(self,
                         message: str,
                         collection_key: str,
                         ttl_per_sec: Optional[int] = None):
        async with self.get_connection() as conn:
            await conn.set(key=collection_key, expire=ttl_per_sec, value=message)
            return collection_key

    @error_logging_handler
    async def get_cached(self,
                         collection_key: str = settings.redis_bonds_list_cache_key):
        async with self.get_connection() as conn:
            return await conn.get(key=collection_key, encoding='utf-8')

    @error_logging_handler
    async def get_key_ttl(self,
                          collection_key: str) -> Optional[int]:
        async with self.get_connection() as conn:
            ttl = await conn.ttl(key=collection_key)
            if ttl == -2:
                return None
            elif ttl == -1:
                return False
            return ttl

    @error_logging_handler
    async def search_by_pattern(self,
                                pattern: str) -> List[str]:
        async with self.get_connection() as conn:
            collection_key = set()
            async for key in conn.iscan(match=pattern):
                collection_key.add(key)
            logging.debug(f'Find keys: {collection_key} by pattern {pattern}')
            tasks = [asyncio.create_task(self.get_cached(item)) for item in collection_key]
            done, pending = await asyncio.wait(tasks, return_when=asyncio.ALL_COMPLETED)
            return [d.result() for d in done]
