from logging import getLogger

from pydantic import BaseSettings

from app.core.logging import setup_logging

setup_logging()
logger = getLogger(__name__)


class Settings(BaseSettings):
    server_host: str = '127.0.0.1'
    server_port: int = 8000
    telegram_token: str
    mongo_host: str = '127.0.0.1'
    mongo_port: int = 27017
    mongo_name: str = 'invest'
    mongo_username: str
    mongo_password: str
    mongo_collection: str = 'notifications'
    telegram_chat_id: str
    time_out: int = 3
    redis_host: str = '127.0.0.1'
    redis_port: int = 6379
    redis_notification_queue: str = 'notification:stock:price:received'
    redis_bonds_list_cache_key: str = 'notification:bonds:default6:received'
    redis_bonds_list_cache_ttl: int = 86400

