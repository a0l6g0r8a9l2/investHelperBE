from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum, unique
from typing import Optional, List

from pydantic import BaseModel, Field
from starlette.status import HTTP_404_NOT_FOUND, HTTP_503_SERVICE_UNAVAILABLE


@unique
class ActionsOnExchange(str, Enum):
    buy = 'Buy'
    sell = 'Sell'


@unique
class Board(str, Enum):
    TQCB = 'Т+: Облигации - безадресные'
    TQOB = 'Т+: Гособлигации - безадресные'


class Message(BaseModel):
    message: str


responses = {
    HTTP_404_NOT_FOUND: {"model": Message},
    HTTP_503_SERVICE_UNAVAILABLE: {"model": Message}
}


class BondFilter(BaseModel):
    cb_key_rate: float = Field(4.5,
                               gt=-1,
                               le=20,
                               description="Ключевая ставка ЦБ",
                               example=4.5)
    min_percent_price: float = Field(95,
                                     gt=50,
                                     le=200,
                                     description="Минимальная цена облигации в % от номинала",
                                     example=95.5)
    max_percent_price: float = Field(105,
                                     gt=50,
                                     le=200,
                                     description="Максимальная цена облигации в % от номинала",
                                     example=105)
    additional_rate: float = Field(1,
                                   gt=-99,
                                   le=99,
                                   description="Дополнительная ставка, которая складыавется с ключеовй ставке ЦБ"
                                               "и используется для фильтрации облигаций по размеру купона, доходности "
                                               "и эффективной доходности",
                                   example=1)
    period: int = Field(547,
                        gt=90,
                        le=3650,
                        description="Колличесво дней, которое планируется держать облигацию. Используется для "
                                    "фильтрации по дате оферты/погашения",
                        example=365)
    boards: List[Board] = [Board.TQCB.name, Board.TQOB.name]
    min_trade_counts: int = Field(100,
                                  gt=1,
                                  description="Минимальное кол-во сделок в периоде",
                                  example=100)
    min_trade_volume: int = Field(10000,
                                  gt=1,
                                  description="Минимальное объем сделок в периоде",
                                  example=10000)
    trade_history_period: int = Field(14,
                                      gt=1,
                                      le=31,
                                      description="Период для фильтрации по кол-ву и объему сделок",
                                      example=14)


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


class BondsRs(BaseModel):
    __root__: List[Bond]


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


class StockPriceNotificationDelete(BaseModel):
    id: str = Field(...,
                    description="Notification ID",
                    min_length=1,
                    max_length=50,
                    example="5f46c2950e4f4ea916ec05ab")


class StockPriceNotificationRead(StockPriceNotificationCreate):
    id: str = Field(...,
                    description="Notification ID",
                    min_length=1,
                    max_length=50,
                    example="5f46c2950e4f4ea916ec05ab")


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


@unique
class ExchangeSuffix(Enum):
    moscow_exchange = '.ME'
    default = str()


@dataclass
class Stock:
    """
    Класс акции
    """

    ticker: str
    shortName: Optional[str] = None
    price: Optional[float] = None
    currency: Optional[str] = None
    currency_symbol: Optional[str] = None

    def __repr__(self):
        if self.price and self.currency_symbol:
            msg = f'{self.ticker}: {self.price} {self.currency_symbol}'
        else:
            msg = f'Price and exchange is not defined for {self.ticker}'
        return msg
