from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum, unique
from typing import Optional

from pydantic import BaseModel, Field
from starlette.status import HTTP_404_NOT_FOUND, HTTP_503_SERVICE_UNAVAILABLE


@unique
class ActionsOnExchange(str, Enum):
    buy = 'Buy'
    sell = 'Sell'


class Message(BaseModel):
    message: str


responses = {
    HTTP_404_NOT_FOUND: {"model": Message},
    HTTP_503_SERVICE_UNAVAILABLE: {"model": Message}
}


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
