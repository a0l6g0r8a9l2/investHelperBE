#!/usr/bin/venv python
# -*- coding: utf-8 -*
import logging
from typing import List

from fastapi import APIRouter, Query, Path
from starlette.status import HTTP_200_OK, HTTP_201_CREATED

from app.core.logging import setup_logging
from app.models.models import StockPriceNotificationReadRs, StockPriceNotificationCreateRq, \
    StockPriceNotificationReadRq, TelegramUser
from app.services.notification import NotificationStockPriceService

setup_logging()
logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/",
             response_model_exclude_none=True,
             status_code=HTTP_201_CREATED,
             response_model=StockPriceNotificationReadRs
             )
async def add_notification_stock_price(data: StockPriceNotificationCreateRq):
    """
    Контролер для создания уведомлений о изменении цены акции
    """
    data.dict(exclude_unset=True)
    logger.debug(f'Request to add_notification_stock_price with data: {data}')
    notification = NotificationStockPriceService()
    return await notification.create(data)


@router.get("/{id}",
            response_model_exclude_none=True,
            status_code=HTTP_200_OK,
            response_model=StockPriceNotificationReadRs,
            )
async def get_notification_stock_price_by_id(id: str = Path(...,
                                                            min_length=3,
                                                            max_length=50,
                                                            description='notification id',
                                                            example='dcf1ae55-52c4-4017-8057-e6168b51773d'),
                                             chatId: str = Query(...,
                                                                 min_length=4,
                                                                 max_length=12,
                                                                 description='telegram chat (user) id',
                                                                 example='411442889')):
    """
    Контролер для чтения уведомлений о изменении цены акции
    """
    logger.debug(f'Request to get_notification_stock_price_by_id with: '
                 f'notification_id: {id}, chatId {chatId}')
    notification = NotificationStockPriceService()
    return await notification.get_one(StockPriceNotificationReadRq(id=id, chatId=chatId))


@router.get("/",
            response_model_exclude_none=True,
            status_code=HTTP_200_OK,
            response_model=List[StockPriceNotificationReadRs],
            )
async def get_all_notification_by_chat_id(chatId: str = Query(...,
                                                              min_length=4,
                                                              max_length=12,
                                                              description='telegram chat (user) id',
                                                              example='411442889')):
    """
    Контролер для чтения уведомлений о изменении цены акции
    """
    # todo: уведомдения не удаляются по истеченю ттл
    logger.debug(f'Request to get_all_notification_stock_price_by_id with: '
                 f'chatId {chatId}')
    notification = NotificationStockPriceService()
    return await notification.get_many(TelegramUser(chatId=chatId))
