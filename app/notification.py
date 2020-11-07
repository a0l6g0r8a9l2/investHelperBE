import asyncio
import logging
from datetime import datetime, timedelta
from enum import unique, Enum
from typing import Optional

import requests
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import load_config
from app.core.logging import setup_logging
from app.db.mongo_db import close_mongo_connection, connect_to_mongo
from app.teleBot import bot
from app.models.models import ActionsOnExchange

# сетап конфиг и логгер
setup_logging()
logger = logging.getLogger(__name__)

default_db = load_config().get("MONGO_NAME")


@unique
class ExchangeCode(Enum):
    moscow_exchange = 'ME'
    default = ''


@unique
class ExchangeSufix(Enum):
    moscow_exchange = '.ME'
    default = ''


@unique
class ExchangeName(Enum):
    moscow_exchange = 'MOSCOW EXCHANGE'
    default = ''


class Exchange:
    """
    Класс биржи, на которой торгуется акция
    """

    def __init__(self,
                 exchange_code: str,
                 exchange_url_sufix: str,
                 exchange_name: Optional[str] = ''):
        self.exchange_code = exchange_code
        self.exchange_name = exchange_name
        self.exchange_url_sufix = exchange_url_sufix

    def __repr__(self):
        return f'{self.exchange_name}'


class Stock(Exchange):
    def __init__(self, ticker: str,
                 exchange_code: str,
                 exchange_url_sufix: str,
                 exchange_name: Optional[str]):
        super().__init__(exchange_code,
                         exchange_url_sufix,
                         exchange_name)
        self.ticker = ticker


class StockPrice(Stock):
    def __init__(self,
                 ticker: str,
                 exchange_code: str,
                 exchange_url_sufix: str,
                 exchange_name: Optional[str],
                 price: float,
                 currency: str,
                 currency_symbol: Optional[str] = None,
                 short_name: Optional[str] = None):
        super().__init__(ticker,
                         exchange_code,
                         exchange_url_sufix,
                         exchange_name)
        self.shortName = short_name
        self.price = price
        self.currency = currency
        self.currency_symbol = currency_symbol

    def __repr__(self):
        return f'Current price for {self.ticker} on {self.exchange_name} is {self.price} {self.currency_symbol}'


async def find_exchange_by_ticker(ticker: str) -> Exchange:
    """
    Функция вызывает yahoo для проверки на какой бирже актив
    :return: Exchange
    """
    _me_url = f'https://query1.finance.yahoo.com/v10/finance/quoteSummary/{ticker}.ME?modules=price'
    _ne_url = f'https://query1.finance.yahoo.com/v10/finance/quoteSummary/{ticker}?modules=price'
    try:
        response = requests.get(_me_url, stream=True, timeout=30)
        if response.json()['quoteSummary'].get("error"):  # есть ошибка - не мск
            exchange = Exchange(exchange_code=ExchangeCode.default.value,
                                exchange_url_sufix=ExchangeSufix.default.value,
                                exchange_name=ExchangeName.default.value)
        else:  # нет ошибки - мск
            exchange = Exchange(exchange_code=ExchangeCode.moscow_exchange.value,
                                exchange_url_sufix=ExchangeSufix.moscow_exchange.value,
                                exchange_name=ExchangeName.moscow_exchange.value)
    except requests.exceptions.HTTPError as err:
        logger.error(f'{err.response.content}')
    else:
        logger.info(f'Return exchange {exchange.exchange_name} for {ticker}')
        return exchange


async def check_price(ticker: str, exchange: Optional[Exchange] = None) -> StockPrice:
    try:
        if not exchange:
            exchange = await find_exchange_by_ticker(ticker)
        _url = f'https://query1.finance.yahoo.com/v10/finance/quoteSummary/{ticker}' \
               f'{exchange.exchange_url_sufix}?modules=price'
        response = requests.get(_url, stream=True, timeout=30)
        price = StockPrice(ticker=ticker,
                           exchange_code=exchange.exchange_code,
                           exchange_url_sufix=exchange.exchange_url_sufix,
                           exchange_name=exchange.exchange_name,
                           short_name=response.json()["quoteSummary"]["result"][0]["price"]["shortName"],
                           price=float(
                               response.json()["quoteSummary"]["result"][0]["price"]["regularMarketPrice"]["raw"]),
                           currency=response.json()["quoteSummary"]["result"][0]["price"]["currency"],
                           currency_symbol=response.json()["quoteSummary"]["result"][0]["price"]["currencySymbol"])
    except (KeyError, TypeError) as err:
        logger.error(f'Getting price error: {err.args}')
    else:
        logger.info(f'Current price for {price.ticker} is {str(price.price) + " " + price.currency_symbol}')
        return price


async def price_checker(notification_id: str,
                        delay: Optional[int] = 60,
                        end_notification: Optional[datetime] = (datetime.now() + timedelta(days=14))):
    db = await connect_to_mongo()  # конектимся
    collection: AsyncIOMotorClient = db[default_db].notification  # получаем коллекцию
    notification_item = await collection.find_one({'_id': ObjectId(notification_id)})
    # получаем конкретный notification
    target_price = notification_item.get("price")
    ticker = notification_item.get("ticker")
    while datetime.now() <= end_notification:
        current_price = await check_price(ticker)
        await asyncio.sleep(delay)
        if current_price.price == target_price or \
                (notification_item.get("action") == str(ActionsOnExchange.buy.value)
                 and current_price.price <= target_price) or \
                (notification_item.get("action") == str(ActionsOnExchange.sell.value)
                 and current_price.price >= target_price):
            logger.info(f'Target price has been reached! id: {notification_id}')
            await task_manager(
                bot.send_message_to_telegram(f'Target price {target_price} for {ticker} has been reached!\n'
                                             f'It is time to {notification_item.get("action")}\n'
                                             f'Event: {notification_item.get("event")}'))
            break
    logger.info(f'Notification time for notification id: {notification_id} is over!')
    await task_manager(bot.send_message_to_telegram(msg=f'Notification time is over for id: {notification_id}!\n'
                                                        f'Ticker: {ticker}\n'
                                                        f'Target price: {target_price}'))
    await collection.find_one_and_delete({'_id': ObjectId(notification_id)})
    await close_mongo_connection()


async def task_manager(coro: asyncio.coroutines, name: Optional[str] = None):
    loop = asyncio.get_event_loop()
    try:
        task_obj = loop.create_task(coro)
        task_obj.set_name(name)
        logger.info(f'Running {task_obj.get_name()}')
    except (NotImplementedError, AttributeError) as err:
        logger.error(f'ERROR {err.args}')
