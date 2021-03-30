import os
import sys
import logging
from logging import getLogger

from app.core.logging import setup_logging

setup_logging()
logger = getLogger(__name__)


def load_config():
    try:
        config_env = str(os.environ.get('BOT_ENV'))
        logging.debug(f'Loaded config {config_env} - OK')
        if config_env != 'PROD':
            from app.core.settings import info
            return info
        else:
            info = {
                "TOKEN": str(os.environ.get('BOT_TOKEN')),
                "BOT_ENV": str(os.environ.get('BOT_ENV')),
                "proxies": None,
                "MONGO_HOST": str(os.environ.get('MONGO_HOST')),
                "MONGO_PORT": int(os.environ.get('MONGO_PORT')),
                "MONGO_NAME": str(os.environ.get('MONGO_NAME')),
                "MONGO_USERNAME": str(os.environ.get('MONGO_USERNAME')),
                "MONGO_PASSWORD": str(os.environ.get('MONGO_PASSWORD')),
                "MONGO_COLLECTION": str(os.environ.get('MONGO_COLLECTION')),
                "CHAT_ID": str(os.environ.get('CHAT_ID')),
                "TIME_OUT": int(os.environ.get('TIME_OUT')),
                "REDIS_HOST": str(os.environ.get('REDIS_HOST')),
                "REDIS_PORT": str(os.environ.get('REDIS_PORT')),
                "REDIS_NOTIFICATION_QUEUE": str(os.environ.get('REDIS_NOTIFICATION_QUEUE')),
                "REDIS_BONDS_LIST_CACHE_KEY": str(os.environ.get('REDIS_BONDS_LIST_CACHE_KEY')),
                "REDIS_BONDS_LIST_CACHE_TTL": int(os.environ.get('REDIS_BONDS_LIST_CACHE_TTL'))
            }
            return info
    except (TypeError, ValueError, ImportError) as err:
        logging.error(f'Invalid config! {err.args}')
        sys.exit(1)
