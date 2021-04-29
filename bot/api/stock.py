#!venv/bin/python
import logging
from typing import List, Dict

import httpx
from pydantic import ValidationError

from bot.api.base import ApiRequest
from bot.core.exceptions import MakeRequestError
from bot.core.logging import setup_logging
from bot.models.models import StockRs

setup_logging()
logger = logging.getLogger(__name__)


class StockService(ApiRequest):
    base_path = '/stocks/'

    async def find_stock_by_ticker(self, ticker: str) -> List[StockRs]:
        """
        Find stocks by ticker using YahooFinance \n
        :return: model: List[Dict]
        """
        try:
            async with httpx.AsyncClient() as client:
                logger.debug(f'Requested url {self.url}')
                url = self.url + ticker.upper()
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()
                stock_list = []
                try:
                    for item in response.json():
                        stock = StockRs(**item)
                        stock_list.append(stock)
                except (ValidationError, TypeError) as ve:
                    logger.warning(f'Error trying deserialize {response.json()}. With args: {ve.errors()}')
                return stock_list
        except httpx.HTTPError as exc:
            logging.error(f'Error from "find_stock_by_ticker": {exc}')
