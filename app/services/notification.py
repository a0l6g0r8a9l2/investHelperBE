import asyncio
import copy
import logging
import random
from asyncio import CancelledError, TimeoutError
from datetime import datetime, timedelta
from functools import partial
from typing import Optional
from uuid import uuid4

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from transitions.extensions.asyncio import AsyncMachine

from app.core.logging import setup_logging
from app.core import settings
from app.db.mongo import MongodbService
from app.db.redis_pub import Redis
from app.models.models import ActionsOnExchange, Stock, ExchangeSuffix, NotificationPayload, NotificationMessage

setup_logging()
logger = logging.getLogger(__name__)


class Notification:
    """
    Класс уведомлений о достижении целевой цены акции

    Args:
        targetPrice - целевая цена акции
        id - идентификатор, получаемый при сохранении в БД
        action - buy/sell:
            если buy - отслеживаем цену targetPrice и меньше,
            если sell -  отслеживаем цену targetPrice и выше
        delay - время между проверкой цены акции
        endNotification - время окончания уведоления
        chatId - идентификатор, чата в телеграмме
    """

    def __init__(self, stock: Stock,
                 targetPrice: float,
                 event: Optional[str] = None,
                 action: Optional[ActionsOnExchange] = ActionsOnExchange.buy.value,
                 delay: Optional[int] = 5,
                 endNotification: Optional[datetime] = (datetime.now() + timedelta(minutes=30)),
                 chatId: str = settings.telegram_chat_id):
        self.stock = stock
        self.targetPrice = targetPrice
        self._id = str(uuid4())
        self.action = action
        self.delay = delay
        self.endNotification = endNotification
        self.chatId = chatId
        self.event = event

    def dict_repr(self) -> dict:
        """
        Возвращает представление в виде словаря

        :return: dict from self.attribute
        """
        stock_dict = copy.deepcopy(self.stock.__dict__)
        notification_dict = copy.deepcopy(self.__dict__)
        notification_dict.pop('stock')
        end_notification = notification_dict.pop('endNotification')
        end_notification = str(end_notification)
        notification_dict.update({'endNotification': end_notification})
        dict_representation = {**notification_dict, **stock_dict}
        logging.debug(f'Log from dict_repr: {dict_representation}')
        return dict_representation

    def __repr__(self):
        return f'Target price: {self.targetPrice}. Current price: {self.stock.price}.'


class NotificationService:
    """
    Класс реализующий flow работы с уведомлениями (Notification) с помощью AsyncMachine (асинхронная машина состояний) и
    AsyncIOScheduler - шедулер отслеживающий цену акции

        states - доступные состояния для AsyncMachine
        _instances - dict с инстансами NotificationService (используется для методов класса)

    """
    states = ['new', 'checking_exchange', 'price_scheduling', 'expired', 'done', 'canceled']
    storage = MongodbService()
    loop = asyncio.get_event_loop()

    def __init__(self, notification: Notification):
        self.notification = notification
        self._url: Optional[str] = None
        self._mongo: MongodbService = MongodbService()
        self._scheduler: [AsyncIOScheduler] = AsyncIOScheduler()
        self.machine = AsyncMachine(model=self, states=NotificationService.states, initial='new')
        self.machine.add_transition(trigger='checking_exchange', source='new', dest='checking_exchange')
        self.machine.add_transition(trigger='price_scheduling', source='checking_exchange', dest='price_scheduling')
        self.machine.add_transition(trigger='time_is_over', source='*', dest='expired', conditions='expired_check')
        self.machine.add_transition(trigger='work_is_done', source=['checking_exchange', 'price_scheduling'],
                                    dest='done')
        self.machine.add_transition(trigger='cancel', source=['new', 'checking_exchange', 'price_scheduling'],
                                    dest='canceled')

    @classmethod
    async def get_notification(cls, notification_id: str):
        """
        Get notification from DB

        :param notification_id: id created notification
        :return: dict repr of Notification
        """
        notification = await cls.storage.get_one_by_id(notification_id)  #
        if notification:
            _id = notification.pop('_id')
            notification.update({'id': _id})
            return notification
        logging.debug(f'Log from get_notification: {notification}')

    @classmethod
    async def delete_notification(cls, notification_id: str):
        """
        Delete notification from DB

        :param notification_id: id created notification
        :return: dict repr of Notification
        """
        notification = await cls.storage.delete_one_by_id(notification_id)
        logging.debug(f'Log from delete_notification: {notification}')
        return notification

    async def on_enter_checking_exchange(self):
        """
        Находит информацию по тикеру в API finance.yahoo.com и формирует url для шедулинга цены

        :return: dict representation of instance
        """
        logging.info(f'Start checking exchange!')
        try:
            urls = [f'https://query1.finance.yahoo.com/v10/finance/quoteSummary/'
                    f'{self.notification.stock.ticker}{s.value}?modules=price' for s in ExchangeSuffix]
            tasks = [asyncio.create_task(asyncio.wait_for(fetch_url(url), timeout=settings.time_out)) for url in urls]
            result_lst = [r for r in await asyncio.gather(*tasks) if r]
            if len(result_lst) != 1:  # stock listed with same ticker on different exchanges
                logging.warning(f'Asset with ticker {self.notification.stock.ticker} found on on different exchanges')
            response: dict = result_lst[0]

            symbol_for_url = response.get("quoteSummary")["result"][0]["price"].get("symbol")
            self._url = f'https://query1.finance.yahoo.com/v10/finance/quoteSummary/{symbol_for_url}?modules=price'
            logging.debug(f'URL for {self.notification.stock.ticker}: {self._url}')

            # set self attribute
            await self.set_self_attr(api_response=response)

            # save notification to DB
            await self._mongo.create_one(self.notification.dict_repr())
            logging.debug(f'notification id {self.notification._id} got from DB')
        except CancelledError:
            done, pending = await asyncio.wait(asyncio.tasks.all_tasks())
            await asyncio.gather(pending)
        except (TimeoutError, httpx.HTTPError, AssertionError) as err:
            logging.error(err.args)
            raise err
        else:
            logging.debug(f'Updated id dict_repr {self.notification.dict_repr()}')
            self.loop.create_task(self.to_price_scheduling())
            return self.notification.dict_repr()

    async def set_self_attr(self, api_response: dict):
        """
        Обновляет атрибуты инстанса Notification после получения актуальной цены

        :param api_response: decoded response from fetch_url()
        :return: None
        """
        try:
            _obj = api_response.get("quoteSummary")["result"][0]["price"]
            self.notification.stock.price = _obj["regularMarketPrice"]["raw"]
            self.notification.stock.currency = _obj["currency"]
            self.notification.stock.currency_symbol = _obj["currencySymbol"]
            self.notification.stock.shortName = _obj["shortName"]
        except (KeyError, AttributeError) as err:
            logging.error(err.args)
        else:
            logging.debug(self.notification.stock)

    async def on_enter_price_scheduling(self):
        """
        Запускает шедулинг цены и проверку на done/expire/cancel

        :return: None
        """
        logging.info(f'State {self.state} and scheduling price for id: {self.notification._id}...')
        try:
            self.loop.create_task(self.send_notification())

            new_price = await asyncio.create_task(asyncio.wait_for(fetch_url(self._url), timeout=settings.time_out))
            set_price = partial(self.set_self_attr, new_price)
            done_check = partial(self.done_check)
            cancel_check = partial(self.cancel_check)
            self._scheduler.add_job(set_price, 'interval', seconds=self.notification.delay,
                                    id=str(self.notification._id + '_set_price'),
                                    name='set_price')
            self._scheduler.add_job(done_check, 'interval',
                                    seconds=self.notification.delay,
                                    id=str(self.notification._id + '_done_check'),
                                    name='done_check')
            self._scheduler.add_job(cancel_check, 'interval',
                                    seconds=self.notification.delay,
                                    id=str(self.notification._id + '_cancel_check'),
                                    name='cancel_check')
            self._scheduler.add_job(self.expired_check, 'interval',
                                    seconds=self.notification.delay,
                                    id=str(self.notification._id + '_expired_check'),
                                    name='expired_check')
            self._scheduler.start()
        except CancelledError:
            done, pending = await asyncio.wait(asyncio.tasks.all_tasks())
            await asyncio.gather(pending)
        except (TimeoutError, httpx.HTTPError) as err:
            raise err

    async def on_enter_done(self):
        logging.info(f'State {self.state} for id: {self.notification._id}!')
        try:
            asyncio.create_task(self.send_notification())
            self._scheduler.shutdown()
        except CancelledError:
            done, pending = await asyncio.wait(asyncio.tasks.all_tasks())
            await asyncio.gather(pending)

    async def on_enter_expired(self):
        logging.info(f'State {self.state} for id: {self.notification._id}!')
        try:
            asyncio.create_task(self.send_notification())
            self._scheduler.shutdown()
        except CancelledError:
            done, pending = await asyncio.wait(asyncio.tasks.all_tasks())
            await asyncio.gather(pending)

    def expired_check(self):
        if datetime.now() >= self.notification.endNotification:
            logging.debug(f'State {self.state} and return expired check {True} for id: {self.notification._id}!')
            self.time_is_over()
            return True
        else:
            logging.debug(f'State {self.state} and return expired check {False} for id: {self.notification._id}!')
            return False

    def done_check(self):
        if self.notification.stock.price == self.notification.targetPrice or \
                (self.notification.action == str(ActionsOnExchange.buy.value)
                 and self.notification.stock.price <= self.notification.targetPrice) or \
                (self.notification.action == str(ActionsOnExchange.sell.value)
                 and self.notification.stock.price >= self.notification.targetPrice):
            self.loop.create_task(self.work_is_done())
            logging.debug(f'State {self.state} and return done check {True}!')
            return True
        else:
            logging.debug(f'State {self.state} and return done check {False}!')
            return False

    async def cancel_check(self):
        try:
            obj = await self.get_notification(self.notification._id)
            logging.debug(f'Cancel_check return: {obj}!')
            if obj:
                logging.debug(f'State {self.state} and return cancel_check {False}!')
                return False
            else:
                logging.debug(f'State {self.state} and return cancel_check {True}!')
                self.loop.create_task(self.cancel())
                return True
        except CancelledError:
            done, pending = await asyncio.wait(asyncio.tasks.all_tasks())
            await asyncio.gather(pending)

    async def on_enter_canceled(self):
        logging.info(f'State {self.state} for id: {self.notification._id}!')
        try:
            asyncio.create_task(self.send_notification())
            self._scheduler.shutdown()
        except CancelledError:
            done, pending = await asyncio.wait(asyncio.tasks.all_tasks())
            await asyncio.gather(pending)

    async def send_notification(self):
        """
        'new', 'checking_exchange', 'price_scheduling', 'expired', 'done', 'canceled'
        :return:
        """
        try:
            payload = ''
            if self.state == 'done':
                payload = NotificationPayload(state='done',
                                              ticker=self.notification.stock.ticker,
                                              action=self.notification.action,
                                              targetPrice=self.notification.targetPrice,
                                              event=self.notification.event,
                                              currentPrice=self.notification.stock.price)
            elif self.state == 'expired':
                payload = NotificationPayload(state='expired',
                                              ticker=self.notification.stock.ticker,
                                              targetPrice=self.notification.targetPrice,
                                              currentPrice=self.notification.stock.price)
            elif self.state == 'canceled':
                payload = NotificationPayload(state='canceled',
                                              id=self.notification._id,
                                              ticker=self.notification.stock.ticker,
                                              targetPrice=self.notification.targetPrice)
            elif self.state == 'price_scheduling':
                payload = NotificationPayload(state='price_scheduling',
                                              id=self.notification._id,
                                              ticker=self.notification.stock.ticker,
                                              action=self.notification.action,
                                              targetPrice=self.notification.targetPrice,
                                              event=self.notification.event,
                                              currentPrice=self.notification.stock.price)
            if payload:
                publisher = Redis()
                message = NotificationMessage(chatId=self.notification.chatId, payload=payload)
                await publisher.start_publish(message=message.json(), queue=settings.redis_notification_queue)
        except Exception as exc:
            logging.error(exc.args)


async def fetch_url(url: str):
    """
    Get response from API by url
    :param url: url
    :return: dict with data.csv from API
    """
    user_agent_lst = ['Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/88.0.4324.104 Safari/537.36',
                      'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:84.0) Gecko/20100101 Firefox/84.0',
                      'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_0) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/75.0.3770.100 Safari/537.36']
    headers = {
        'authority': 'query1.finance.yahoo.com',
        'user-agent': random.choice(user_agent_lst)
    }
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(url, headers=headers)
            response = r.json()
            r.raise_for_status()
        return response
    except httpx.HTTPError as exc:
        logging.warning(f'HTTP Exception - {exc}')
        return None
