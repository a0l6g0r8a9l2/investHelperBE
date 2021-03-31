from typing import Optional, List
from datetime import datetime, timedelta

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
