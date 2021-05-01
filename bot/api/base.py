import logging

from bot.core import settings
from bot.core.logging import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


class ApiRequest:
    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/json',
    }
    host = settings.server_host
    port = settings.server_port
    base_path = '/'

    @property
    def url(self):
        # f'{self.host}:{self.port}{self.base_path}'
        return f'http://{self.host}:{self.port}{self.base_path}'
