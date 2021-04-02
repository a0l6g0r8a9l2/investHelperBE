#!venv/bin/python
import logging
from datetime import datetime, timedelta
from typing import Optional

import httpx
from pydantic import ValidationError

from bot.api.base import ApiRequest
from bot.core.exceptions import PrepareRequestError, MakeRequestError
from bot.core.logging import setup_logging
from bot.models.models import StockPriceNotificationCreateBot, StockPriceNotificationCreateApiRq

setup_logging()
logger = logging.getLogger(__name__)


class NotificationService(ApiRequest):
    base_path = '/notification/'

    def __init__(self, notification_user_data: StockPriceNotificationCreateBot):
        self.notification_user_data = notification_user_data

    async def create_notification(self) -> Optional[dict]:
        """
        Create notification

        :return: dict with data from API
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(self.url, headers=self.headers, content=self.params.json())
                logging.debug(
                    f'Log from {self.create_notification.__name__}: '
                    f'status: {response.status_code}')
                if response.status_code != 201:
                    raise MakeRequestError(f'HTTP error with: {response.status_code}, {response.content}')
                else:
                    response = response.json()
                    return response
        except httpx.HTTPError as exc:
            logging.error(f'Error from {__name__}: {exc}')

    @property
    def params(self) -> StockPriceNotificationCreateApiRq:
        try:
            bot_notification = self.notification_user_data.dict()
            logging.debug(f'Log from {__name__}: user_data: {bot_notification}')

            end_notification, delay = bot_notification['endNotification'], bot_notification['delay']
            bot_notification['endNotification'] = self.convert_period_to_datetime(end_notification)
            bot_notification['delay'] = self.convert_period_to_seconds(delay)

            request_params = StockPriceNotificationCreateApiRq(**bot_notification)
            return request_params
        except (KeyError, ValueError, ValidationError) as err:
            logging.error(f'Log from prepare_request: {err.args}')
            raise PrepareRequestError(f'Could not prepare request from user typed data')

    def convert_period_to_datetime(self, period: str) -> datetime:
        date_time = datetime.now() + timedelta(seconds=self.convert_period_to_seconds(period))
        return date_time

    @staticmethod
    def convert_period_to_seconds(period: str) -> int:
        converter = {"s": 1, "m": 60, "h": 3600, "d": 86400}
        converted_period = int(period[:-1]) * converter.get(period[-1])
        return converted_period
