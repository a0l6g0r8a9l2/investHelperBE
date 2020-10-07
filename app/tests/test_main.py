import asyncio

import pytest
from httpx import AsyncClient

from app.db.mongo_db import connect_to_mongo
from app.main import app


@pytest.yield_fixture(scope='session')
def event_loop(request):
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.mark.asyncio
async def test_root():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_create_notification():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        await connect_to_mongo()
        response = await ac.post("/stocks/notification/", json={
            "ticker": "MOEX",
            "price": 127.5,
            "action": "Buy",
            "event": "the price has reached a monthly low",
            "endNotification": "2020-10-04T20:45:28.560039",
            "delay": 60
        })
    assert response.status_code == 201
    return response.json().get('id')


@pytest.mark.asyncio
async def test_read_notification():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        notification_id = await test_create_notification()
        response = await ac.get(f"/stocks/notification/{notification_id}")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_delete_notification():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        notification_id = await test_create_notification()
        response = await ac.delete(f"/stocks/notification/{notification_id}")
    assert response.status_code == 204
