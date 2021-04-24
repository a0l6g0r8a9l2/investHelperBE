import asyncio
import logging
from asyncio import CancelledError
from typing import Optional, List

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
        except CancelledError:
            done, pending = await asyncio.wait(asyncio.tasks.all_tasks())
            await asyncio.gather(pending)
        finally:
            redis.close()
            await redis.wait_closed()

    async def save_cache(self,
                         message: str,
                         collection_key: str,
                         ttl_per_sec: Optional[int] = None):
        redis = await aioredis.create_redis(self.redis_connection_string, encoding='utf-8')
        try:
            cache = await redis.set(key=collection_key, expire=ttl_per_sec, value=message)
            if cache:
                logging.debug(f'Message saved to redis key: {collection_key}, ttl: {ttl_per_sec} sec')
            else:
                raise RedisError(f'Error trying to save message')
            return collection_key
        except RedisError as redis_err:
            logging.error(f'Redis error: {redis_err.args}')
        except CancelledError:
            done, pending = await asyncio.wait(asyncio.tasks.all_tasks())
            await asyncio.gather(pending)
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
        except CancelledError:
            done, pending = await asyncio.wait(asyncio.tasks.all_tasks())
            await asyncio.gather(pending)
        finally:
            redis.close()
            await redis.wait_closed()

    async def get_key_ttl(self,
                          collection_key: str) -> Optional[int]:
        redis = await aioredis.create_redis(self.redis_connection_string, encoding='utf-8')
        try:
            ttl = await redis.ttl(key=collection_key)
            if ttl == -2:
                return None
            elif ttl == -1:
                return False
            logging.debug(f'TTL {ttl} got from redis to key: {collection_key}')
            return ttl
        except RedisError as redis_err:
            logging.error(f'Redis error: {redis_err.args}')
        except CancelledError:
            done, pending = await asyncio.wait(asyncio.tasks.all_tasks())
            await asyncio.gather(pending)
        finally:
            redis.close()
            await redis.wait_closed()

    async def search_by_pattern(self,
                                pattern: str) -> List[str]:
        redis = await aioredis.create_redis(self.redis_connection_string, encoding='utf-8')
        try:
            collection_key = set()
            async for key in redis.iscan(match=pattern):
                collection_key.add(key)
            logging.debug(f'Find keys: {collection_key} by pattern {pattern}')
            tasks = [asyncio.create_task(self.get_cached(item)) for item in collection_key]
            done, pending = await asyncio.wait(tasks, return_when=asyncio.ALL_COMPLETED)
            return [d.result() for d in done]
        except RedisError as redis_err:
            logging.error(f'Redis error: {redis_err.args}')
        except CancelledError:
            done, pending = await asyncio.wait(asyncio.tasks.all_tasks())
            await asyncio.gather(pending)
        finally:
            redis.close()
            await redis.wait_closed()
