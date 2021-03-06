import logging
from typing import List

import motor.motor_asyncio
from pymongo.errors import PyMongoError

from app.core import settings
from app.core.logging import setup_logging

# сетап конфиг и логгер
setup_logging()
logger = logging.getLogger(__name__)


class MongodbService:
    """
    Class for async CRUD document in Mongo
    """
    _instance = None
    _client = None
    _db = None

    def __init__(self, host: str = settings.mongo_host, port: int = settings.mongo_port,
                 db: str = settings.mongo_name, collection: str = settings.mongo_collection):
        self._client = motor.motor_asyncio.AsyncIOMotorClient(host, port)
        self._db = self._client[db]
        self._collection = self._db[collection]

    async def create_one(self, dto) -> str:
        """
        Create document in Mongo

        :param dto: document
        :return: id document in Mongo
        """
        try:
            async with await self._client.start_session() as s:
                result = await self._collection.insert_one(dto, session=s)
                return str(result.inserted_id)
        except PyMongoError as err:
            logging.error(err.args)

    async def get_one_by_id(self, doc_id: str) -> dict:
        """
        Return document from Mongo by id

        :param doc_id: id document in Mongo
        :return: dict
        """
        try:
            async with await self._client.start_session() as s:
                return await self._collection.find_one({'_id': doc_id}, session=s)
        except PyMongoError as err:
            logging.error(err.args)

    async def update_one_by_id(self, doc_id: str, fields: List[dict]):
        """
        Update one or more fields in document

        :param doc_id: id document in Mongo
        :param fields: List[field:value]
        :return: None
        """
        try:
            async with await self._client.start_session() as s:
                for item in fields:
                    await self._collection.update_one({'_id': doc_id}, {'$set': item}, session=s)
        except PyMongoError as err:
            logging.error(err.args)

    async def delete_one_by_id(self, doc_id: str):
        try:
            async with await self._client.start_session() as s:
                await self._collection.find_one_and_delete({'_id': doc_id}, session=s)
        except PyMongoError as err:
            logging.error(err.args)

    async def delete_all(self):
        try:
            async with await self._client.start_session() as s:
                n0 = await self._collection.count_documents({}, session=s)
                logging.debug(f'Before deleting {n0} documents')
                await self._collection.delete_many({})
                n1 = await self._collection.count_documents({}, session=s)
                logging.debug(f'After deleting {n1} documents')
        except PyMongoError as err:
            logging.error(err.args)

    async def get_all_collection_items(self) -> List[dict]:
        try:
            async with await self._client.start_session() as s:
                cursor = self._collection.find({}, session=s).sort('i')
                documents = await cursor.to_list(length=1000)
                return documents
        except PyMongoError as err:
            logging.error(err.args)

    def __repr__(self):
        return f'DB: {self._db.name} Collection: {self._collection.name}'
