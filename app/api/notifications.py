#!/usr/bin/venv python
# -*- coding: utf-8 -*
import logging
import sys

import httpx
from fastapi import Path, APIRouter
from starlette.responses import JSONResponse
from starlette.status import HTTP_204_NO_CONTENT, HTTP_400_BAD_REQUEST, HTTP_500_INTERNAL_SERVER_ERROR, \
    HTTP_404_NOT_FOUND, HTTP_200_OK, HTTP_201_CREATED, HTTP_503_SERVICE_UNAVAILABLE
from transitions import MachineError

from app.core.logging import setup_logging
from app.models.models import StockPriceNotificationReadRs, StockPriceNotificationCreateRq, responses, Stock
from app.services.notification import Notification, NotificationService

setup_logging()
logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/",
             response_model_exclude_none=True,
             status_code=HTTP_201_CREATED,
             responses={**responses},
             response_model=StockPriceNotificationReadRs
             )
async def add_notification_stock_price(notification_request: StockPriceNotificationCreateRq):
    """
    Контролер для создания уведомлений о изменении цены акции
    """
    try:
        notification_request.dict(exclude_unset=True)
        logging.debug(notification_request)
        stock = Stock(ticker=notification_request.ticker.upper())
        notification_model = Notification(stock=stock,
                                          targetPrice=notification_request.targetPrice,
                                          action=notification_request.action,
                                          event=notification_request.event,
                                          delay=notification_request.delay,
                                          endNotification=notification_request.endNotification,
                                          chatId=notification_request.chatId)
        service = NotificationService(notification_model)
        await service.checking_exchange()  # todo: pretty name for first state
        notification = await service.get_notification(notification_model._id)
        response = StockPriceNotificationReadRs(**notification)
        return response
    except (KeyError, ValueError, AttributeError, MachineError) as v_err:
        logging.error(v_err.args)
        return JSONResponse(status_code=HTTP_400_BAD_REQUEST, content={"message": f"Error with value {v_err}"})
    except (TimeoutError, httpx.HTTPError) as t_err:
        tb = sys.exc_info()[2]
        logging.error(t_err.args, t_err.with_traceback(tb))
        return JSONResponse(status_code=HTTP_503_SERVICE_UNAVAILABLE,
                            content={"message": "Connection refused"},
                            headers={"Retry-After": 30})
    except Exception as e_err:
        tb = sys.exc_info()[2]
        logging.error(e_err.args, e_err.with_traceback(tb))
        return JSONResponse(status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                            content={"message": "Internal Server Error"})


@router.get("/{id}",
            response_model_exclude_none=True,
            status_code=HTTP_200_OK,
            response_model=StockPriceNotificationReadRs,
            responses={**responses}
            )
async def get_notification_stock_price_by_id(id: str = Path(...,
                                                            description="notification id",
                                                            min_length=1,
                                                            max_length=50,
                                                            example="5f46c2950e4f4ea916ec05ab"
                                                            )):
    """
    Контролер для чтения уведомлений о изменении цены акции
    """
    try:
        notification = await NotificationService.get_notification(id)
        response = StockPriceNotificationReadRs(**notification)
        return response
    except (KeyError, ValueError, AttributeError, MachineError) as v_err:
        logging.error(v_err.args)
        return JSONResponse(status_code=HTTP_400_BAD_REQUEST, content={"message": f"Item '{v_err}' not found"})
    except (TimeoutError, httpx.HTTPError) as t_err:
        tb = sys.exc_info()[2]
        logging.error(t_err.args, t_err.with_traceback(tb))
        return JSONResponse(status_code=HTTP_503_SERVICE_UNAVAILABLE,
                            content={"message": "Connection refused"},
                            headers={"Retry-After": 30})
    except Exception as e_err:
        tb = sys.exc_info()[2]
        logging.error(e_err.args, e_err.with_traceback(tb))
        return JSONResponse(status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                            content={"message": "Internal Server Error"})


@router.delete("/{id}",
               response_model_exclude_none=True,
               status_code=HTTP_204_NO_CONTENT,
               responses={**responses}
               )
async def delete_notification_stock_price_by_id(id: str = Path(...,
                                                               description="notification id",
                                                               min_length=1,
                                                               max_length=50,
                                                               example="5f46c2950e4f4ea916ec05ab"
                                                               )):
    """
    Контролер для удаления уведомлений о изменении цены акции
    """
    try:
        await NotificationService.delete_notification(id)
        return JSONResponse(status_code=HTTP_204_NO_CONTENT)
    except (KeyError, ValueError, AttributeError, MachineError) as v_err:
        logging.error(v_err.args)
        return JSONResponse(status_code=HTTP_404_NOT_FOUND, content={"message": "Item not found"})
    except (TimeoutError, httpx.HTTPError) as t_err:
        tb = sys.exc_info()[2]
        logging.error(t_err.args, t_err.with_traceback(tb))
        return JSONResponse(status_code=HTTP_503_SERVICE_UNAVAILABLE,
                            content={"message": "Connection refused"},
                            headers={"Retry-After": 30})
    except Exception as e_err:
        tb = sys.exc_info()[2]
        logging.error(e_err.args, e_err.with_traceback(tb))
        return JSONResponse(status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                            content={"message": "Internal Server Error"})
