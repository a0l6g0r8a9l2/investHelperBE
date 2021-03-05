import os
import sys
from logging import getLogger

logger = getLogger(__name__)


def load_config():
    try:
        config_env = str(os.environ.get('BOT_ENV'))
        logger.debug(f'Loaded config {config_env} - OK')
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
                "REDIS_PORT": int(os.environ.get('REDIS_PORT')),
            }
            return info
    except (TypeError, ValueError, ImportError) as err:
        logger.error(f'Invalid config! {err.args}')
        sys.exit(1)
