import logging

from bot.core import cfg
from bot.core.logging import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


class ApiRequest:
    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/json',
    }
    host = cfg.get("NOTIFICATION_SERVICE_HOST")
    port = cfg.get("NOTIFICATION_SERVICE_PORT")
    base_path = '/'

    @property
    def url(self):
        return f'http://{self.host}:{self.port}{self.base_path}'
