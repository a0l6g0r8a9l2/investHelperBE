from pydantic import BaseSettings


class Settings(BaseSettings):
    server_host: str = '127.0.0.1'
    server_port: int = 8000
    telegram_token: str
    telegram_chat_id: str
    time_out: int = 5
    redis_host: str = '127.0.0.1'
    redis_port: int = 6379
    redis_notification_queue: str = 'notification:stock:price:received'
