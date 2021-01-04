#!/usr/bin/venv python
# -*- coding: utf-8 -*
import logging
import sys

import httpx
import uvicorn
from fastapi import FastAPI, Path
from fastapi.responses import RedirectResponse
from starlette.responses import JSONResponse
from starlette.status import HTTP_204_NO_CONTENT, HTTP_400_BAD_REQUEST, HTTP_500_INTERNAL_SERVER_ERROR, \
    HTTP_404_NOT_FOUND, HTTP_200_OK, HTTP_201_CREATED, HTTP_503_SERVICE_UNAVAILABLE
from transitions import MachineError

from app.core.logging import setup_logging
from app.models.models import StockPriceNotificationRead, StockPriceNotificationCreate, responses, Stock
from app.services.notification import Notification, NotificationService

# сетап конфиг и логгер
setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="InvestHelper",
              description="This is API for InvestHelperBot",
              version="0.1.1")


@app.get("/", include_in_schema=False)
def docs_redirect():
    return RedirectResponse(f"{app.root_path}/docs")


@app.post("/stocks/notification/",
          response_model_exclude_none=True,
          status_code=HTTP_201_CREATED,
          responses={**responses},
          response_model=StockPriceNotificationRead,
          tags=["stocks"])
async def add_notification_stock_price(notification_request: StockPriceNotificationCreate):
    """
    Контролер для создания уведомлений о изменении цены акции
    """
    try:
        notification_request.dict(exclude_unset=True)
        logging.debug(notification_request)
        stock = Stock(ticker=notification_request.ticker)
        notification_model = Notification(stock=stock,
                                          targetPrice=notification_request.targetPrice,
                                          action=notification_request.action,
                                          event=notification_request.event,
                                          delay=notification_request.delay,
                                          endNotification=notification_request.endNotification,
                                          chatId=notification_request.chatId)
        service = NotificationService(notification_model)
        await service.checking_exchange()
        await service.price_scheduling()
        response = StockPriceNotificationRead(**service.notification.dict_repr())
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


@app.get("/stocks/notification/{id}",
         response_model_exclude_none=True,
         status_code=HTTP_200_OK,
         response_model=StockPriceNotificationRead,
         responses={**responses},
         tags=["stocks"])
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
        notification: dict = NotificationService.get_instance_by_notification_id(id).notification.dict_repr()
        response = StockPriceNotificationRead(**notification)
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


@app.delete("/stocks/notification/{id}",
            response_model_exclude_none=True,
            status_code=HTTP_204_NO_CONTENT,
            responses={**responses},
            tags=["stocks"])
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
        notification = NotificationService.get_instance_by_notification_id(id)
        await notification.cancel()
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


if __name__ == '__main__':
    uvicorn.run(app, log_config=setup_logging())
