import asyncio
import logging
from asyncio import CancelledError
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import uuid4

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import HTTPException
from pydantic import ValidationError
from starlette import status
from transitions.extensions import AsyncMachine

from app.core import settings
from app.core.logging import setup_logging
from app.db.redis_pub import Redis
from app.models.models import (StockPriceNotificationCreateRq,
                               StockPriceNotificationReadRs,
                               StockPriceNotificationReadRq,
                               TelegramUser,
                               StockPriceNotificationDeleteRq,
                               StockRq, ActionsOnExchange,
                               )
from app.services.stock import StockService

# todo: add some tests
setup_logging()
logger = logging.getLogger(__name__)


class NotificationStockPriceService:
    """
    Base class to manage notification
    """
    states = ["new", "in_progress", "disabled", "done"]

    def __init__(self):
        self.notification: Optional[StockPriceNotificationReadRs] = None
        self.stock_service = StockService()
        self.storage = Redis()
        self.scheduler = AsyncIOScheduler()
        self.__price_cache_key = None
        self.__notification_cache_key = None
        self.__loop = asyncio.get_event_loop()
        self.machine = AsyncMachine(model=self, states=NotificationStockPriceService.states, initial='new')
        self.machine.add_transition(trigger='start', source='new', dest='in_progress',
                                    unless=['is_expired', 'is_finished'])
        self.machine.add_transition(trigger='to_expired', source='*', dest='disabled', conditions='is_expired')
        self.machine.add_transition(trigger='to_done', source='in_progress', dest='done')
        self.machine.add_transition(trigger='stop', source=['new', 'in_progress'], dest='disabled')

    @property
    def price_cache_key(self) -> str:
        return self.__price_cache_key

    @property
    def notification_cache_key(self) -> str:
        return self.__notification_cache_key

    @notification_cache_key.setter
    def notification_cache_key(self, value):
        self.__notification_cache_key = value

    @property
    def created_notification(self) -> Optional[StockPriceNotificationReadRs]:
        return self.notification

    @property
    def notification_ttl(self) -> Optional[int]:
        if self.notification:
            return (self.notification.endNotification - datetime.now()).seconds
        else:
            return None

    async def create(self, notification: StockPriceNotificationCreateRq) -> StockPriceNotificationReadRs:
        """
        Create notification and save it to storage \n
        :param notification: model: StockPriceNotificationCreateRq
        :return: model: StockPriceNotificationReadRs
        """
        try:
            notification_id = str(uuid4())
            logger.info(f'Creating notification {notification_id}..')
            self.__price_cache_key = f'stock:price:{notification.ticker}'
            self.notification_cache_key = self.get_notification_cache_key(notification_id=notification_id,
                                                                          chatId=notification.chatId)

            stock_rq_data = StockRq(**notification.dict())
            current_stock_amount = await self.stock_service.get_stock_price(stock_rq_data)
            response = StockPriceNotificationReadRs(**notification.dict(),
                                                    id=notification_id,
                                                    currentPrice=current_stock_amount,
                                                    state='new')
            self.notification = response
            logger.debug(f'Build model: {response}')

            await asyncio.gather(
                self.storage.save_cache(
                    message=str(current_stock_amount.value),
                    collection_key=self.price_cache_key,
                    ttl_per_sec=notification.delay
                ),
                self.storage.save_cache(
                    message=response.json(),
                    collection_key=self.notification_cache_key,
                    ttl_per_sec=self.notification_ttl
                ))

            logger.info(f'Notification {notification_id} is created')
            await self.machine.dispatch('start')
            return response
        except ValidationError as ve:
            logger.error(f'Validation error while trying creating notification: {ve}')
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=f'{ve.errors()}')
        except CancelledError:
            done, pending = await asyncio.wait(asyncio.tasks.all_tasks())
            await asyncio.gather(pending)

    async def on_enter_in_progress(self):
        """
        Run price scheduling and done/expired checks
        :return:
        """
        try:
            self.scheduler.add_job(self.update_price,
                                   trigger='interval',
                                   seconds=self.created_notification.delay,
                                   id=f'update_price_{self.created_notification.id}',
                                   name='update_price'
                                   )

            self.scheduler.add_job(self.is_finished,
                                   trigger='interval',
                                   seconds=self.created_notification.delay,
                                   id=f'done_check_{self.created_notification.id}',
                                   name='done_check'
                                   )
            self.scheduler.add_job(self.is_expired,
                                   trigger='interval',
                                   seconds=self.created_notification.delay,
                                   id=f'expired_check_{self.created_notification.id}',
                                   name='expired_check'
                                   )
            self.scheduler.start()
        except CancelledError:
            done, pending = await asyncio.wait(asyncio.tasks.all_tasks())
            await asyncio.gather(pending)

    async def update_price(self):
        """
        Update price and save it to storage
        :return:
        """
        try:
            notification = await self.get_cached_notification()
            if notification:
                actual_price = await self.get_actual_price()
                notification.currentPrice.value = actual_price
                notification.state = self.state

                await self.storage.save_cache(
                    message=notification.json(),
                    collection_key=self.notification_cache_key,
                    ttl_per_sec=self.notification_ttl
                )
                logger.debug(f'Price updated: {notification.currentPrice.value}')
            else:
                await self.machine.dispatch('to_expired')
        except CancelledError:
            done, pending = await asyncio.wait(asyncio.tasks.all_tasks())
            await asyncio.gather(pending)

    async def get_cached_price(self) -> Optional[Decimal]:
        try:
            price = await self.storage.get_cached(self.price_cache_key)
            logger.debug(f'Cached price is: {price}')
            if price:
                return Decimal(price)
            else:
                return None
        except CancelledError:
            done, pending = await asyncio.wait(asyncio.tasks.all_tasks())
            await asyncio.gather(pending)

    async def get_cached_notification(self) -> Optional[StockPriceNotificationReadRs]:
        try:
            notification_json = await self.storage.get_cached(self.notification_cache_key)
            notification: StockPriceNotificationReadRs = StockPriceNotificationReadRs.parse_raw(notification_json)
            logger.debug(f'Cached notification: {notification.id}')
            return notification
        except ValidationError:
            logger.warning(f'Cant deserialize cached notification. Probably it is no longer exist')
            return None
        except CancelledError:
            done, pending = await asyncio.wait(asyncio.tasks.all_tasks())
            await asyncio.gather(pending)

    async def get_actual_price(self) -> Decimal:
        """
        Getting actual price from API or return in from cache
        :return: Decimal
        """
        try:
            ttl_cached_price = await self.storage.get_key_ttl(self.price_cache_key)
            cached_price = await self.get_cached_price()
            if not (ttl_cached_price or cached_price) or ttl_cached_price > self.created_notification.delay:
                logger.debug(f'Cached price is not actual. Getting price..')
                current_price = await self.stock_service.get_stock_price(StockRq(**self.created_notification.dict()))
                await self.storage.save_cache(str(current_price.value), collection_key=self.price_cache_key)
                return Decimal(current_price.value)
            else:
                logger.debug(f'Cached price is actual')
                return cached_price
        except CancelledError:
            done, pending = await asyncio.wait(asyncio.tasks.all_tasks())
            await asyncio.gather(pending)

    async def is_finished(self) -> bool:
        notification = await self.get_cached_notification()
        if not notification:
            logger.debug(f'Done check return {False}!')  # expired
            return False
        elif notification.currentPrice.value == self.created_notification.targetPrice or \
                (self.created_notification.action == str(ActionsOnExchange.buy.value)
                 and notification.currentPrice.value <= self.created_notification.targetPrice) or \
                (self.created_notification.action == str(ActionsOnExchange.sell.value)
                 and notification.currentPrice.value >= self.created_notification.targetPrice):
            logger.debug(f'Done check return {True}!')
            asyncio.create_task(self.machine.dispatch('to_done'))
            return True
        else:
            logger.debug(f'Done check return {False}!')
            return False

    async def on_enter_done(self):
        try:
            logger.info(f'Notification {self.created_notification.id} is Done! Sending message..')
            asyncio.create_task(self.send())
            self.scheduler.shutdown()
        except CancelledError:
            done, pending = await asyncio.wait(asyncio.tasks.all_tasks())
            await asyncio.gather(pending)

    async def is_expired(self):
        try:
            notification_json = await self.storage.get_cached(self.notification_cache_key)
            if notification_json:
                notification: StockPriceNotificationReadRs = StockPriceNotificationReadRs.parse_raw(notification_json)
                logger.debug(f'Notification {notification.id} is no expired')
                return False
            else:
                logger.debug(f'Can not return cached notification: notification is expired')
                return True
        except ValidationError:
            logger.error(f'Error getting cached notification!')

    async def on_enter_disabled(self):
        try:
            logger.info(f'Notification {self.created_notification.id} is Disabled! Sending message..')
            asyncio.create_task(self.send())
            self.scheduler.shutdown()
        except CancelledError:
            done, pending = await asyncio.wait(asyncio.tasks.all_tasks())
            await asyncio.gather(pending)

    async def send(self):
        """
        Send serialized message to storage
        :return:
        """
        try:
            notification_json = await self.storage.get_cached(self.notification_cache_key)
            if notification_json:
                notification: StockPriceNotificationReadRs = StockPriceNotificationReadRs.parse_raw(notification_json)
            else:
                notification = self.created_notification
            notification.state = self.state
            logger.debug(f'Sending message {notification.json()}')
            await self.storage.start_publish(message=notification.json(), queue=settings.redis_notification_queue)
        except CancelledError:
            done, pending = await asyncio.wait(asyncio.tasks.all_tasks())
            await asyncio.gather(pending)

    async def get_one(self, notification: StockPriceNotificationReadRq) -> StockPriceNotificationReadRs:
        """
        Get notification by user chatId and notification id
        :param notification: model: StockPriceNotificationReadRq
        :return: model: StockPriceNotificationReadRs
        """
        try:
            self.notification_cache_key = self.get_notification_cache_key(notification_id=notification.id,
                                                                          chatId=notification.chatId)
            cached_notification = await self.get_cached_notification()
            if cached_notification:
                message = StockPriceNotificationReadRs(**cached_notification.dict(), state=self.state)
                logger.debug(f'Return notification {message}')
                return message
            else:
                raise HTTPException(
                    status_code=404,
                    detail=f'Item {notification.id} not found'
                )
        except CancelledError:
            done, pending = await asyncio.wait(asyncio.tasks.all_tasks())
            await asyncio.gather(pending)

    @classmethod
    def get_notification_cache_key(cls, chatId: str, notification_id: str = '*') -> str:
        return f'notification:{chatId}:{notification_id}'

    async def get_many(self, user: TelegramUser) -> List[StockPriceNotificationReadRs]:
        """
        Get all user notification \n
        :param user: model: TelegramUser
        :return: List[StockPriceNotificationReadRs]
        """
        try:
            row_notifications = await self.storage.search_by_pattern(
                self.get_notification_cache_key(chatId=user.chatId))
            response = []
            for item in row_notifications:
                try:
                    obj = StockPriceNotificationReadRs.parse_raw(item)
                except ValidationError as ve:
                    logger.warning(f'Error trying deserialize {item}: {ve}')
                else:
                    response.append(obj)
            return response
        except CancelledError:
            done, pending = await asyncio.wait(asyncio.tasks.all_tasks())
            await asyncio.gather(pending)

    async def delete_one(self, notification: StockPriceNotificationDeleteRq):
        raise NotImplementedError

    async def delete_many(self, user: TelegramUser):
        raise NotImplementedError
