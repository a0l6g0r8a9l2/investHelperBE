from motor.motor_asyncio import AsyncIOMotorClient
import logging
from app.core.config import load_config


# MongoDB
class MongoDB:
    client: AsyncIOMotorClient = None


db = MongoDB()


async def get_nosql_db() -> AsyncIOMotorClient:
    return db.client


async def connect_to_mongo():
    db.client = AsyncIOMotorClient(
        f'mongodb+srv://{load_config().get("mongo_username")}:{load_config().get("mongo_password")}@invest-mvp-gb0oh'
        f'.mongodb.net/invest?retryWrites=true&w=majority',
        maxPoolSize=load_config().get("MAX_CONNECTIONS_COUNT"),
        minPoolSize=load_config().get("MIN_CONNECTIONS_COUNT"),
    )
    logging.info("connected to mongodb")
    return db.client


async def close_mongo_connection():
    db.client.close()
    logging.info("closed mongo connection")