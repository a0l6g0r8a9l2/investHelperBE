#!venv/bin/python
import logging
import sys
from datetime import datetime, timedelta
from typing import Optional

import httpx

from bot.core import config_data
from bot.core.exceptions import PrepareRequestError, MakeRequestError
from bot.core.logging import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


class NotificationService:
    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/json',
    }
    host = config_data.get("NOTIFICATION_SERVICE_HOST")
    port = config_data.get("NOTIFICATION_SERVICE_PORT")
    base_path = '/stocks/notification/'
    url = f'http://{host}:{port}{base_path}'

    async def create(self, tg_notification: dict, url: Optional[str] = None, headers: Optional[dict] = None) -> dict:
        """
        Create notification

        :param tg_notification: notification from bot
        :param headers: headers for request
        :param url: url
        :return: dict with data from API
        """
        params = self._prepare_request_params(tg_notification=tg_notification)

        if not headers:
            headers = self.headers
        if not url:
            url = self.url

        try:
            async with httpx.AsyncClient() as client:
                logging.debug(f'Log from {self.create.__name__}: url: {url}')
                r = await client.post(url, headers=headers, json=params)
                response = r.json()
                logging.debug(
                    f'Log from {self.create.__name__}: url: {url}, status: {r.status_code}, response: {response}')
                r.raise_for_status()
            return response
        except httpx.HTTPError as exc:
            logging.error(f'HTTP Exception - {exc}')
            raise MakeRequestError(f'HTTP error with: {exc.with_traceback(sys.exc_info()[2])}')

    @staticmethod
    def _prepare_request_params(tg_notification: dict) -> dict:
        try:
            if tg_notification.get('price'):
                tg_notification['targetPrice'] = float(tg_notification.pop('price'))
            if tg_notification.get('end_notification').endswith('m'):
                tg_notification['endNotification'] = str(
                    datetime.now() + timedelta(minutes=int(tg_notification.pop('end_notification')[:-1])))
            elif tg_notification.get('end_notification').endswith('h'):
                tg_notification['endNotification'] = str(
                    datetime.now() + timedelta(hours=int(tg_notification.pop('end_notification')[:-1])))
            elif tg_notification.get('end_notification').endswith('d'):
                tg_notification['endNotification'] = str(
                    datetime.now() + timedelta(days=int(tg_notification.pop('end_notification')[:-1])))
            if tg_notification.get('delay').endswith('s'):
                tg_notification['delay'] = int(tg_notification.get('delay')[:-1])
            elif tg_notification.get('delay').endswith('m'):
                tg_notification['delay'] = int(tg_notification.get('delay')[:-1]) * 60
            elif tg_notification.get('delay').endswith('h'):
                tg_notification['delay'] = int(tg_notification.get('delay')[:-1]) * 60 * 60
            return tg_notification
        except (KeyError, ValueError) as err:
            logging.error(f'Log from _prepare_request_params: {err.args}')
            raise PrepareRequestError(f'Could not prepare request from data')
