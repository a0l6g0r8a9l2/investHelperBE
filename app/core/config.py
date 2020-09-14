import os
import sys
from logging import getLogger

logger = getLogger(__name__)


def load_config():
    try:
        info = {
            "token": os.environ.get('API_TOKEN'),
            "conf_name": os.environ.get('BOT_ENV'),
            "proxies": None,
            "mongo_name": os.environ.get('DB_NAME'),
            "mongo_username": os.environ.get('DB_USER'),
            "mongo_password": os.environ.get('DB_PASSWORD'),
            "mongo_collection": os.environ.get('DB_COLLECTION'),
            "MAX_CONNECTIONS_COUNT": os.environ.get('MAX_CONNECTIONS_COUNT'),
            "MIN_CONNECTIONS_COUNT": os.environ.get('MIN_CONNECTIONS_COUNT')
        }
        logger.debug(f'Loaded config {info["conf_name"]} - OK')
        if info.get("conf_name") != 'prod':
            from app.core.settings import info
            return info
        else:
            return info
    except (TypeError, ValueError, ImportError) as err:
        logger.error(f'Invalid config! {err.args}')
        sys.exit(1)
