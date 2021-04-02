from datetime import datetime, timedelta
from enum import unique, Enum
from typing import Optional

from pydantic import BaseModel, Field
from starlette.status import HTTP_503_SERVICE_UNAVAILABLE, HTTP_201_CREATED, HTTP_400_BAD_REQUEST


class MessageRs(BaseModel):
    message: str


class MessageRq(MessageRs):
    chatId: str


responses = {
    HTTP_503_SERVICE_UNAVAILABLE: {"model": MessageRs},
    HTTP_201_CREATED: {"model": MessageRs},
    HTTP_400_BAD_REQUEST: {"model": MessageRs}
}


@unique
class ActionsOnExchange(str, Enum):
    buy = 'Buy'
    sell = 'Sell'


class StockPriceNotificationCreate(BaseModel):
    ticker: str = Field(...,
                        description="The ticker length must be greater than one and less then 6",
                        min_length=1,
                        max_length=5,
                        example="MOEX")
    targetPrice: float = Field(...,
                               gt=0,
                               description="The price must be greater than zero",
                               example=127.5)
    action: Optional[ActionsOnExchange] = None
    event: Optional[str] = Field(None,
                                 description="Describe event, if necessary",
                                 min_length=1,
                                 max_length=100,
                                 example="the price has reached a monthly low")


class StockPriceNotificationCreateBot(StockPriceNotificationCreate):
    endNotification: str = Field(...,
                                 description="End notification period",
                                 regex="^\d{1,2}\w{1,2}$",
                                 example="3h")
    delay: str = Field(...,
                       description="Checking price delay",
                       regex="^\d{1,2}\w{1,2}$",
                       example="3h")


class StockPriceNotificationCreateApiRq(StockPriceNotificationCreate):
    endNotification: Optional[datetime] = Field(datetime.now() + timedelta(days=14),
                                                description="The date must be greater than now",
                                                example=datetime.now() + timedelta(minutes=5))
    delay: int = Field(60,
                       gt=9,
                       le=86400,
                       description="Seconds before next check price",
                       example=60)
    chatId: str = Field(411442889,
                        description="Yours telegram chat id",
                        min_length=5,
                        max_length=12,
                        example="411442889")


class NotificationPayload(BaseModel):
    id: Optional[str]
    state: str
    ticker: str
    action: str
    event: Optional[str]
    targetPrice: float
    currentPrice: Optional[float]


class NotificationMessage(BaseModel):
    chatId: str
    payload: NotificationPayload


class Bond(BaseModel):
    isin: str = Field(...,
                      description="ISIN код облигации",
                      regex='^[A-Z0-9]{12}$',
                      example='RU000A0ZZWZ9')
    name: str = Field(...,
                      description="Наименование облигации",
                      example='Детский мир ПАО БО-07')
    couponAmount: float = Field(...,
                                gt=0,
                                description="Сумма купона в валюте",
                                example=17.01)
    accumulatedCouponYield: float = Field(None,
                                          description="Накопленный купонный доход",
                                          example=17.01)
    couponPeriod: int = Field(...,
                              description="Периодичность выплаты купона в днях",
                              example=182)
    couponPercent: float = Field(...,
                                 description="Накопленный купонный доход",
                                 example=6.75)
    price: float = Field(...,
                         gt=0,
                         description="Цена облигации в % от номинала",
                         example=92.75)
    nextCouponDate: datetime = Field(None,
                                     description="Дата следующего купона",
                                     example=datetime.now() + timedelta(days=90))
    expiredDate: datetime = Field(...,
                                  description="Дата экспирации/оферты",
                                  example=datetime.now() + timedelta(days=182))
    yieldToOffer: Optional[float] = Field(None,
                                          description="Доходность к оферте",
                                          example=6.3471)
    effectiveYield: Optional[float] = Field(None,
                                            description="Эффективная доходность",
                                            example=6.3471)

    class Config:
        allow_population_by_field_name = True
