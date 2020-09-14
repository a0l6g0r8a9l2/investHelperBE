from typing import Optional
from enum import Enum, unique
from datetime import datetime, timedelta

from pydantic import BaseModel, Field


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
    price: float = Field(...,
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


class StockPriceNotificationDelete(BaseModel):
    id: str = Field(...,
                    description="Notification ID",
                    min_length=1,
                    max_length=50,
                    example="fdfsdfsdf-dasdasdas-46546546")


class StockPriceNotificationUpdate(BaseModel):
    id: str = Field(...,
                    description="Notification ID",
                    min_length=1,
                    max_length=10,
                    example="fdfsdfsdf-dasdasdas-46546546")
    price: Optional[float] = Field(...,
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
                                                example=datetime.now())


class StockPriceNotificationRead(StockPriceNotificationCreate):
    id: str = Field(...,
                    description="Notification ID",
                    min_length=1,
                    max_length=50,
                    example="fdfsdfsdf-dasdasdas-46546546")
