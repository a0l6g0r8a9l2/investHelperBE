from typing import Optional

from pydantic import BaseModel
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
