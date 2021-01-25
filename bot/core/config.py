import os
import sys
from logging import getLogger

logger = getLogger(__name__)


def load_config():
    try:
        config_env = str(os.environ.get('BOT_ENV'))
        logger.debug(f'Loaded config {config_env} - OK')
        if config_env != 'PROD':
            from bot.core.settings import info
            return info
        else:
            info = {
                "TELEGRAM_API_TOKEN": str(os.environ.get('TELEGRAM_API_TOKEN')),
                "TELEGRAM_ACCESS_ID": os.environ.get('TELEGRAM_ACCESS_ID'),
                "NOTIFICATION_SERVICE_HOST": str(os.environ.get('NOTIFICATION_SERVICE_HOST')),
                "NOTIFICATION_SERVICE_PORT": str(os.environ.get('NOTIFICATION_SERVICE_PORT')),
                "BOT_ENV": str(os.environ.get('BOT_ENV')),
                "TIME_OUT": int(os.environ.get('TIME_OUT'))
            }
            return info
    except (TypeError, ValueError, ImportError) as err:
        logger.error(f'Invalid config! {err.args}')
        sys.exit(1)
