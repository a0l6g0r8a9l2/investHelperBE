import logging
from typing import List

from fastapi import (APIRouter, status, Path)

from app.core.logging import setup_logging
from app.models.models import StockRs, FindStockRq
from app.services.notification import StockService

router = APIRouter()

setup_logging()
logger = logging.getLogger(__name__)


@router.get("/{ticker}",
            response_model_exclude_none=True,
            status_code=status.HTTP_200_OK,
            response_model=List[StockRs]
            )
async def get_stocks_by_ticker(ticker: str = Path(...,
                                                  description="Stock ticker",
                                                  min_length=1,
                                                  max_length=5,
                                                  example="MOEX")):
    """
    Контролер поиска акции по тикеру
    """
    logger.debug(f'Request to get_stocks_by_ticker with: ticker {ticker}')
    stock_service = StockService()
    return await stock_service.find_stocks_by_ticker(FindStockRq(ticker=ticker))
