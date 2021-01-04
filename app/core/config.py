import os
import sys
from logging import getLogger

logger = getLogger(__name__)


def load_config():
    try:
        info = {
            "TOKEN": os.environ.get('API_TOKEN'),
            "CONF_NAME": os.environ.get('BOT_ENV'),
            "proxies": None,
            "MONGO_NAME": os.environ.get('DB_NAME'),
            "MONGO_USERNAME": os.environ.get('DB_USER'),
            "MONGO_PASSWORD": os.environ.get('DB_PASSWORD'),
            "MONGO_COLLECTION": os.environ.get('DB_COLLECTION'),
            "MAX_CONNECTIONS_COUNT": os.environ.get('MAX_CONNECTIONS_COUNT'),
            "MIN_CONNECTIONS_COUNT": os.environ.get('MIN_CONNECTIONS_COUNT'),
            "CHAT_ID": os.environ.get('CHAT_ID'),
            "TIME_OUT": os.environ.get('TIME_OUT')
        }
        logger.debug(f'Loaded config {info["CONF_NAME"]} - OK')
        if info.get("CONF_NAME") != 'PROD':
            from app.core.settings import info
            return info
        else:
            return info
    except (TypeError, ValueError, ImportError) as err:
        logger.error(f'Invalid config! {err.args}')
        sys.exit(1)
