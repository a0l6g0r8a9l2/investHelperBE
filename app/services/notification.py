import asyncio
import copy
import logging
from asyncio.exceptions import CancelledError, TimeoutError
from datetime import datetime, timedelta
from functools import partial
from typing import Optional

import httpx
from aiogram import Bot
from aiogram.utils.exceptions import TelegramAPIError
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from transitions.extensions.asyncio import AsyncMachine

from app.core import config_data
from app.core.logging import setup_logging
from app.db.mongo import MongodbService
from app.models.models import ActionsOnExchange, Stock, ExchangeSuffix

# сетап конфиг и логгер
setup_logging()
logger = logging.getLogger(__name__)

TIME_OUT = config_data.get("TIME_OUT")


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
                 id: Optional[str] = None,
                 event: Optional[str] = None,
                 action: Optional[ActionsOnExchange] = ActionsOnExchange.buy.value,
                 delay: Optional[int] = 5,
                 endNotification: Optional[datetime] = (datetime.now() + timedelta(minutes=30)),
                 chatId: str = config_data.get("CHAT_ID")):
        self.stock = stock
        self.targetPrice = targetPrice
        self.id = id
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
        logger.debug(dict_representation)
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
    _instances = {}

    def __init__(self, notification: Notification):
        self.notification = notification
        self._url: Optional[str] = None
        self._mongo: MongodbService = MongodbService()
        self._scheduler: [AsyncIOScheduler] = AsyncIOScheduler()
        self.machine = AsyncMachine(model=self, states=NotificationService.states, initial='new')
        self.machine.add_transition(trigger='checking_exchange', source='new', dest='checking_exchange')
        self.machine.add_transition(trigger='price_scheduling', source='checking_exchange', dest='price_scheduling',
                                    unless='expired_check')
        self.machine.add_transition(trigger='time_is_over', source='*', dest='expired')
        self.machine.add_transition(trigger='work_is_done', source='price_scheduling', dest='done',
                                    conditions='done_check')
        self.machine.add_transition(trigger='cancel', source=['new', 'checking_exchange', 'price_scheduling'],
                                    dest='canceled')

    @classmethod
    def get_instance_by_notification_id(cls, notification_id):
        """
        Получить инстанс класса по notification_id.
        Можно использовать для смены состояния инстанса из вне

        :param notification_id: идентификатор инстанса класса уведомлений
        :return: инстанс NotificationService
        :raise: ValueError, если идентификатор инстанса класса уведомлений не найден
        """
        for k, v in cls._instances.items():
            if k == notification_id:
                return v
        raise ValueError(notification_id)

    @classmethod
    def __delete_instance_by_notification_id(cls, notification_id):
        """
        Приватный класс удаления

        :param notification_id: идентификатор инстанса класса уведомлений
        :return: True
        :raise: KeyError, если идентификатор инстанса класса уведомлений не найден
        """
        try:
            cls._instances.pop(notification_id)
        except KeyError as err:
            logging.error(err.args)
        else:
            return True

    async def on_enter_checking_exchange(self):
        """
        Находит информацию по тикеру в API finance.yahoo.com и формирует url для шедулинга цены

        :return: dict representation of instance
        """
        logging.info(f'Start checking exchange!')
        try:
            urls = [f'https://query1.finance.yahoo.com/v10/finance/quoteSummary/'
                    f'{self.notification.stock.ticker}{s.value}?modules=price' for s in ExchangeSuffix]
            tasks = [asyncio.create_task(asyncio.wait_for(fetch_url(url), timeout=TIME_OUT)) for url in urls]
            result_lst = [r for r in await asyncio.gather(*tasks) if r]
            assert len(result_lst) == 1  # stock listed with same ticker on different exchanges
            response: dict = result_lst[0]

            symbol_for_url = response.get("quoteSummary")["result"][0]["price"].get("symbol")
            self._url = f'https://query1.finance.yahoo.com/v10/finance/quoteSummary/{symbol_for_url}?modules=price'
            logging.debug(f'URL for {self.notification.stock.ticker}: {self._url}')

            # set self attribute
            self.set_self_attr(api_response=response)

            # save notification to DB and set notification.id
            self.notification.id = await self._mongo.create_one(self.notification.dict_repr())

            # update dict of class instances
            self._instances.update({self.notification.id: self})
            logging.debug(f'notification id {self.notification.id} got from DB')
        except CancelledError:
            done, pending = asyncio.wait(*asyncio.tasks.all_tasks())
            await asyncio.gather(pending)
        except (TimeoutError, httpx.HTTPError, AssertionError) as err:
            logging.error(err.args)
            raise err
        else:
            logging.debug(f'Updated id dict_repr {self.notification.dict_repr()}')
            return self.notification.dict_repr()

    def set_self_attr(self, api_response: dict):
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
        Запускает шедулинг цены и done_check()

        :return: None
        """
        logging.info(f'State {self.state} and scheduling price for id: {self.notification.id}...')
        try:
            new_price = await asyncio.create_task(asyncio.wait_for(fetch_url(self._url), timeout=TIME_OUT))
            set_price = partial(self.set_self_attr, new_price)
            self._scheduler.add_job(set_price, 'interval', seconds=self.notification.delay, id=self.notification.id)
            self._scheduler.start()
            check_price = await self.done_check()
            if check_price:
                await self.work_is_done()
        except CancelledError:
            done, pending = asyncio.wait(*asyncio.tasks.all_tasks())
            await asyncio.gather(pending)
        except (TimeoutError, httpx.HTTPError) as err:
            raise err

    async def on_enter_done(self):
        logging.info(f'State {self.state} for id: {self.notification.id}!')
        try:
            asyncio.create_task(self.send_notification())
            self._scheduler.shutdown()
        except CancelledError:
            done, pending = asyncio.wait(*asyncio.tasks.all_tasks())
            await asyncio.gather(pending)

    async def on_enter_expired(self):
        logging.info(f'State {self.state} for id: {self.notification.id}!')
        try:
            asyncio.create_task(self.send_notification())
        except CancelledError:
            done, pending = asyncio.wait(*asyncio.tasks.all_tasks())
            await asyncio.gather(pending)

    async def expired_check(self):
        if datetime.now() >= self.notification.endNotification:
            logging.debug(f'State {self.state} and return expired check {True} for id: {self.notification.id}!')
            await self.time_is_over()
            return True
        else:
            logging.debug(f'State {self.state} and return expired check {False} for id: {self.notification.id}!')
            return False

    async def done_check(self):
        """
        Проверяет достигла ли цена целевого значения
        :return:
            True, если цена достигла целевого значения
            False, иначе
        """
        if self.notification.stock.price == self.notification.targetPrice or \
                (self.notification.action == str(ActionsOnExchange.buy.value)
                 and self.notification.stock.price <= self.notification.targetPrice) or \
                (self.notification.action == str(ActionsOnExchange.sell.value)
                 and self.notification.stock.price >= self.notification.targetPrice):
            logging.debug(f'State {self.state} and return done check {True}!')
            return True
        else:
            logging.debug(f'State {self.state} and return done check {False}!')
            return False

    async def on_enter_canceled(self):
        logging.info(f'State {self.state} for id: {self.notification.id}!')
        try:
            asyncio.create_task(self.send_notification())
            self.__delete_instance_by_notification_id(self.notification.id)
        except CancelledError:
            done, pending = asyncio.wait(*asyncio.tasks.all_tasks())
            await asyncio.gather(pending)

    async def send_notification(self):
        """
        'new', 'checking_exchange', 'price_scheduling', 'expired', 'done', 'canceled'
        :return:
        """
        try:
            msg = ''
            if self.state == 'done':
                if self.notification.action:
                    msg2 = f'You can {self.notification.action}!'
                else:
                    msg2 = ''
                msg = f'Target {self.notification.targetPrice} has reached! ' \
                      f'Current price is {self.notification.stock.price}. ' + msg2
            elif self.state == 'expired':
                msg = f'Notification life time is over! Target {self.notification.targetPrice}. ' \
                      f'Current price is {self.notification.stock.price}.'
            elif self.state == 'canceled':
                msg = f'Notification {self.notification.id} is canceled!'
            if msg:
                bot = Bot(token=config_data.get("TOKEN"))
                await bot.send_message(chat_id=self.notification.chatId, text=msg)
                await bot.close()
        except TelegramAPIError as tae:
            logging.error(tae.args)


async def fetch_url(url: str):
    """
    Get response from API by url
    :param url: url
    :return: dict with data from API
    """
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(url)
            response = r.json()
            r.raise_for_status()
        return response
    except httpx.HTTPError as exc:
        logging.error(f'HTTP Exception - {exc}')
        return None


# end_notify1 = datetime.now() + timedelta(seconds=-5)
# _notification = Notification(stock=Stock(ticker='MOEX'), endNotification=end_notify1,
#                             action=ActionsOnExchange.buy.value, targetPrice=121.1)
# notify1 = NotificationService(notification=_notification)
# print(notify1.notification)

# asyncio.get_event_loop().run_until_complete(notify1.checking_exchange())
# asyncio.get_event_loop().run_until_complete(notify1.price_scheduling())
# получить dict repr инстанса для влзвращения в api
# print(notify1.get_instance_by_notification_id('test_notification_id').notification.dict_repr())
# получить инстанс для чтения/отмены
# notify2 = NotificationService.get_instance_by_notification_id('test_notification_id')
# print(notify2.notification)
# asyncio.get_event_loop().run_until_complete(notify2.cancel())
# asyncio.get_event_loop().run_until_complete(asyncio.sleep(10))
# asyncio.get_event_loop().run_until_complete(notify1.cancel())
# asyncio.get_event_loop().run_forever()
