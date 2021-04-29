import asyncio
import logging
import random
from asyncio import CancelledError
from typing import Optional, List

import httpx

from app.core.logging import setup_logging
from app.models.models import (StockRs, ExchangeSuffix, ExchangeRs, FindStockRq, Amount, StockRq, AssetProfile)

setup_logging()
logger = logging.getLogger(__name__)


class YahooApiService:
    """
    Base class for calling YahooApi
    """
    __user_agent_lst = ['Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                        'Chrome/88.0.4324.104 Safari/537.36',
                        'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:84.0) Gecko/20100101 Firefox/84.0',
                        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_0) AppleWebKit/537.36 (KHTML, like Gecko) '
                        'Chrome/75.0.3770.100 Safari/537.36']
    __headers = {
        'authority': 'query1.finance.yahoo.com',
        'user-agent': random.choice(__user_agent_lst)
    }

    @classmethod
    async def fetch_data(cls, url: str):
        """
        Get response from API by url
        :param url: url
        :return: dict with data from API
        """

        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(url, headers=cls.__headers)
                response = r.json()
                logger.info(f'Response from YahooFinance: {r.status_code}')
                r.raise_for_status()
            return response
        except httpx.HTTPError as exc:
            logger.warning(f'HTTP Exception: {exc}')


class StockService(YahooApiService):
    """
    Base class for stock
    """
    module = 'price'

    async def find_stocks_by_ticker(self, stock: FindStockRq) -> Optional[List[StockRs]]:
        """
        Функция по тикеру возвращает представление
        инструмента на каждой из бирж

        :param stock: (ticker - тикер)
        :return: список представлений инструмента на каждой из бирж
        """
        logger.info(f'Start checking exchange!')

        response_list = []
        try:
            yahoo_symbol_list = [stock.ticker + i for i in ExchangeSuffix]
            urls = [f'https://query1.finance.yahoo.com/v10/finance/quoteSummary/'
                    f'{s}?modules={self.module}' for s in yahoo_symbol_list]
            tasks = [asyncio.create_task(asyncio.wait_for(self.fetch_data(url), timeout=3)) for url in
                     urls]
            result_lst = [r.get("quoteSummary")["result"][0]["price"] for r in await asyncio.gather(*tasks) if r]

            for item in result_lst:
                exchange = ExchangeRs(
                    code=item.get("exchange"),
                    name=item.get("exchangeName"),
                    yahoo_search_symbol=item.get("symbol")
                )
                amount = Amount(
                    value=item["regularMarketPrice"].get("raw"),
                    currency=item.get("currency"),
                    currency_symbol=item.get("currencySymbol")
                )
                asset_profile = await self.stock_profile(StockRq(ticker=item.get("symbol").partition('.')[0],
                                                                 exchange=exchange))
                asset = StockRs(
                    shortName=item.get("shortName"),
                    price=amount,
                    ticker=item.get("symbol").partition('.')[0],
                    exchange=exchange,
                    assetProfile=asset_profile
                )
                response_list.append(asset)
            logger.debug(f'Returning objects: {response_list}')
            return response_list
        except CancelledError:
            done, pending = await asyncio.wait(asyncio.tasks.all_tasks())
            await asyncio.gather(pending)

    async def get_stock_price(self, stock: StockRq) -> Amount:
        """
        Getting stock price from YahooApi
        :param stock: model: StockRq
        :return: model: Amount
        """
        try:
            url = f'https://query1.finance.yahoo.com/v10/finance/quoteSummary/' \
                  f'{stock.exchange.yahoo_search_symbol}?modules={self.module}'
            response = await asyncio.create_task(asyncio.wait_for(self.fetch_data(url), timeout=3))
            price = response.get("quoteSummary")["result"][0]["price"]
            amount = Amount(
                value=price["regularMarketPrice"].get("raw"),
                currency=price.get("currency"),
                currency_symbol=price.get("currencySymbol")
            )
            logger.debug(f'Return amount {amount}')
            return amount
        except AttributeError:
            logger.error(f'No such price for {stock.exchange.yahoo_search_symbol}')
        except CancelledError:
            done, pending = await asyncio.wait(asyncio.tasks.all_tasks())
            await asyncio.gather(pending)

    async def stock_profile(self, stock: StockRq) -> AssetProfile:
        module = 'assetProfile'
        try:
            url = f'https://query1.finance.yahoo.com/v10/finance/quoteSummary/' \
                  f'{stock.exchange.yahoo_search_symbol}?modules={module}'
            response = await asyncio.create_task(asyncio.wait_for(self.fetch_data(url), timeout=3))
            profile_root: dict = response.get("quoteSummary")["result"][0][module]
            asset_profile = AssetProfile(
                industry=profile_root.get('industry'),
                sector=profile_root.get('sector'),
                site=profile_root.get('website')
            )
            logger.debug(f'Return profile: {asset_profile}')
            return asset_profile
        except CancelledError:
            done, pending = await asyncio.wait(asyncio.tasks.all_tasks())
            await asyncio.gather(pending)
