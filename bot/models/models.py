from datetime import datetime, timedelta
from decimal import Decimal
from enum import unique, Enum
from typing import Optional

from pydantic import BaseModel, Field


@unique
class ActionsOnExchange(str, Enum):
    buy = 'Buy'
    sell = 'Sell'


class Amount(BaseModel):
    value: Decimal = Field(...,
                           description='Asset price',
                           example=Decimal('171.73'))
    currency: str = Field(...,
                          description='Asset currency code',
                          example='RUB')
    currency_symbol: str = Field(...,
                                 description='Asset currency symbol',
                                 example='руб.')


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


class AssetProfile(BaseModel):
    industry: str = Field(...,
                          description='Asset industry',
                          example='Financial Data & Stock Exchanges')
    sector: str = Field(...,
                        description='Asset sector',
                        example='Financial Services')
    site: Optional[str] = Field(...,
                                description='Asset company website',
                                example='http://www.moex.com')


class ExchangeRs(BaseModel):
    code: Optional[str] = Field(None,
                                description='YahooFinance exchange code',
                                example='.ME')
    name: Optional[str] = Field(None,
                                description='Exchange name',
                                example='MCX')
    yahoo_search_symbol: str = Field(None,
                                     description='YahooFinance search symbol',
                                     example='MOEX.ME')


class StockRq(BaseModel):
    ticker: str = Field(...,
                        description="The ticker length must be greater than one and less then 6",
                        min_length=1,
                        max_length=5,
                        example="MOEX")
    exchange: ExchangeRs


class StockRs(StockRq):
    shortName: Optional[str] = Field(None,
                                     description='Asset short name',
                                     example='MOSCOW EXCHANGE')
    price: Amount
    assetProfile: Optional[AssetProfile] = None


class StockPriceNotificationCreateRq(StockRq):
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
    chatId: str = Field('411442889',
                        description="Yours telegram chat id",
                        min_length=5,
                        max_length=12,
                        example="411442889")


class StockPriceNotificationReadRs(StockPriceNotificationCreateRq):
    id: str = Field(...,
                    description="Notification ID",
                    min_length=1,
                    max_length=50,
                    example="5f46c2950e4f4ea916ec05ab")
    currentPrice: Amount
    state: Optional[str] = None


class StockPriceNotificationRqBot(StockPriceNotificationCreate):
    endNotification: str = Field(...,
                                 description="End notification period",
                                 regex="^\d{1,2}\w{1,2}$",
                                 example="3h")
    delay: str = Field(...,
                       description="Checking price delay",
                       regex="^\d{1,2}\w{1,2}$",
                       example="3h")
    chatId: str = Field('411442889',
                        description="Yours telegram chat id",
                        min_length=5,
                        max_length=12,
                        example="411442889")
    exchange: ExchangeRs


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
