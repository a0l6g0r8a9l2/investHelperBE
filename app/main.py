#!/usr/bin/venv python
# -*- coding: utf-8 -*

import logging

import uvicorn
from bson import ObjectId
from fastapi import FastAPI, status, HTTPException, Depends, Path
from fastapi.encoders import jsonable_encoder
from motor.motor_asyncio import AsyncIOMotorCollection

from app.core.config import load_config
from app.core.logging import setup_logging
from app.db.mongo_db import close_mongo_connection, connect_to_mongo, get_nosql_db, AsyncIOMotorClient
from app.models.models import StockPriceNotificationCreate, StockPriceNotificationRead
from app.notification import task_manager, price_checker

# сетап конфиг и логгер
setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="InvestHelper",
              description="This is API for InvestHelperBot",
              version="0.1.0")

default_db = load_config().get("mongo_name")


@app.on_event("startup")
async def startup_event():
    try:
        await connect_to_mongo()
    except HTTPException as e:
        logging.info(e.headers)


@app.on_event("shutdown")
async def shutdown_event():
    await close_mongo_connection()


@app.post("/stocks/notification/",
          response_model_exclude_none=True,
          status_code=status.HTTP_201_CREATED,
          response_model=StockPriceNotificationRead,
          tags=["stocks"])
async def add_notification_stock_price(notification: StockPriceNotificationCreate,
                                       db_client: AsyncIOMotorClient = Depends(get_nosql_db)):
    """
    Контролер для создания уведомлений о изменении цены акции
    """
    db = db_client[default_db]
    collection: AsyncIOMotorCollection = db.notification
    notification.dict(exclude_unset=True)  # исключим из вх. данных не переданные опциональные параметры
    encoded_notification = jsonable_encoder(notification)  # на входе pydantic модель, которую необходимо
    notification_id = await collection.insert_one(encoded_notification)  # TODO: Вызовы в контролеры
    await task_manager(price_checker(str(notification_id.inserted_id), end_notification=notification.endNotification))
    response = {"id": str(notification_id.inserted_id), **notification.dict()}
    return response


@app.get("/stocks/notification/{id}",
         response_model_exclude_none=True,
         status_code=status.HTTP_200_OK,
         response_model=StockPriceNotificationRead,
         tags=["stocks"])
async def get_notification_stock_price_by_id(id: str = Path(...,
                                                            description="notification id",
                                                            min_length=1,
                                                            max_length=100,
                                                            example="5f46c2950e4f4ea916ec05ab"
                                                            ),
                                             db_client: AsyncIOMotorClient = Depends(get_nosql_db)):
    """
    Контролер для чтения уведомлений о изменении цены акции
    """
    db = db_client[default_db]
    collection: AsyncIOMotorCollection = db.notification
    notification: dict = await collection.find_one({'_id': ObjectId(id)})  # TODO: Вызовы в контролеры
    _id = str(notification.pop('_id'))
    notification['id'] = _id
    response = StockPriceNotificationRead(**notification)
    return response


@app.delete("/stocks/notification/{id}",
            response_model_exclude_none=True,
            status_code=status.HTTP_204_NO_CONTENT,
            tags=["stocks"])
async def delete_notification_stock_price_by_id(id: str = Path(...,
                                                               description="notification id",
                                                               min_length=1,
                                                               max_length=100,
                                                               example="5f46c2950e4f4ea916ec05ab"
                                                               ),
                                                db_client: AsyncIOMotorClient = Depends(get_nosql_db)):
    """
    Контролер для чтения уведомлений о изменении цены акции
    """
    db = db_client[default_db]
    collection: AsyncIOMotorCollection = db.notification
    await collection.find_one_and_delete({'_id': ObjectId(id)})


if __name__ == '__main__':
    uvicorn.run(app)
