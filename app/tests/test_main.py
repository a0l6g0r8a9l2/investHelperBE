import asyncio

import pytest

from app.db.redis_pub import Redis


@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()


@pytest.fixture()
async def sleep_fixture():
    return await asyncio.sleep(1)


redis = Redis()
redis_test_collection = 'test:collections'
redis_test_message = 'test message'
redis_new_test_message = 'new test message'
redis_test_ttl = 4


@pytest.mark.asyncio
async def test_redis_save_to_cache(event_loop):
    cached_collection = await redis.save_cache(collection_key=redis_test_collection,
                                               message=redis_test_message,
                                               ttl_per_sec=redis_test_ttl)
    assert cached_collection == redis_test_collection


@pytest.mark.asyncio
async def test_redis_get_from_cache(event_loop):
    cached_message = await redis.get_cached(collection_key=redis_test_collection)
    assert cached_message == redis_test_message


@pytest.mark.asyncio
async def test_redis_update_cached(event_loop):
    cached_collection = await redis.save_cache(collection_key=redis_test_collection,
                                               message=redis_new_test_message)
    assert cached_collection == redis_test_collection


@pytest.mark.asyncio
async def test_redis_get_ttl(event_loop):
    key_ttl = await redis.get_key_ttl(collection_key=redis_test_collection)
    assert key_ttl == redis_test_ttl


@pytest.mark.asyncio
async def test_redis_ttl_decrease(sleep_fixture):
    key_ttl = await redis.get_key_ttl(collection_key=redis_test_collection)
    assert key_ttl < redis_test_ttl


@pytest.mark.asyncio
async def test_redis_search_by_pattern(sleep_fixture):
    messages = await redis.search_by_pattern(pattern=redis_test_collection)
    assert len(messages) > 0


@pytest.mark.asyncio
async def test_redis_cache_expired(event_loop):
    await asyncio.sleep(redis_test_ttl)
    cached_message = await redis.get_cached(collection_key=redis_test_collection)
    assert cached_message is None
