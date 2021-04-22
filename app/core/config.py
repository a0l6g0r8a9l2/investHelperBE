from pydantic import BaseSettings


class Settings(BaseSettings):
    server_host: str = '127.0.0.1'
    server_port: int = 8000
    telegram_token: str = '1482285686:AAELI4Uhzf_ql49fgohczkTGbyZailNJHtg'
    mongo_host: str = '127.0.0.1'
    mongo_port: int = 27017
    mongo_name: str = 'invest'
    mongo_username: str = 'invest-bot'
    mongo_password: str = 'invest-bot'
    mongo_collection: str = 'notifications'
    telegram_chat_id: str = '411442889'
    time_out: int = 5
    redis_host: str = '127.0.0.1'
    redis_port: int = 6379
    redis_notification_queue: str = 'notification:stock:price:received'
    redis_bonds_list_cache_key: str = 'notification:bonds:default6:received'
    redis_bonds_list_cache_ttl: int = 86400

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'
