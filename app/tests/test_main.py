from datetime import datetime, timedelta

import httpx
import pytest

url = 'http://127.0.0.1'
port = '8000'
root_path = f'{url}:{port}'

json = {
    "ticker": "MOEX",
    "targetPrice": 127.5,
    "action": "Buy",
    "event": "the price has reached a monthly low",
    "endNotification": str(datetime.now() + timedelta(minutes=5)),
    "delay": 60,
    "chatId": "411442889"
}

notification_id = ''


@pytest.mark.asyncio
async def test_root():
    async with httpx.AsyncClient() as client:
        response = await client.get(f'{root_path}/docs')
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_create_notification():
    async with httpx.AsyncClient() as client:
        response = await client.post(f'{root_path}/stocks/notification/', json=json)
        assert response.status_code == 201
        global notification_id
        notification_id = response.json().get('id')


@pytest.mark.asyncio
async def test_read_notification():
    async with httpx.AsyncClient() as client:
        response = await client.get(f'{root_path}/stocks/notification/{notification_id}')
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_delete_notification():
    async with httpx.AsyncClient() as client:
        response = await client.delete(f'{root_path}/stocks/notification/{notification_id}')
        assert response.status_code == 204
