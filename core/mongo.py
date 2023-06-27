import logging
from typing import Optional

from certifi import where
from pymongo import ReturnDocument
from pymongo.errors import ConfigurationError, ServerSelectionTimeoutError
from motor.motor_asyncio import (
    AsyncIOMotorClient,
    AsyncIOMotorDatabase,
    AsyncIOMotorCollection,
    AsyncIOMotorClientSession
)


class MongoDBClient:

    """
    Responsible for handling all MongoDB operations.

    This class can either be instantiated normally or by using an asynchronous context manager.
    """

    def __init__(self, connection_uri: str):
        try:
            self.client: AsyncIOMotorClient = AsyncIOMotorClient(
                connection_uri,
                tlsCAFile=where(),
                serverSelectionTimeoutMS=3000
            )

        except ConfigurationError:
            logging.fatal('Invalid Mongo connection URI provided.')
            raise SystemExit()

        self.database: AsyncIOMotorDatabase = self.client.database

        self.userdata: AsyncIOMotorCollection = self.database.userdata
        self.settings: AsyncIOMotorCollection = self.database.settings

        self._session = None

    async def __aenter__(self):
        try:
            self._session: AsyncIOMotorClientSession = await self.client.start_session()
        except ServerSelectionTimeoutError:
            logging.fatal('Failed to connect to MongoDB. Please check your credentials.')
            raise SystemExit()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> bool:
        await self._session.end_session()
        return False

    @staticmethod
    def _default_settings(discord_id: int) -> dict:
        return {
            'discord_id': discord_id,
            'stay_signed_in': True,
            'auto_research': False,
            'auto_free_llamas': False
        }

    async def search_settings_entry(self, discord_id: int) -> dict:
        data = await self.settings.find_one({'discord_id': discord_id}, session=self._session)

        if data is None:
            default = self._default_settings(discord_id)
            await self.settings.insert_one(default, session=self._session)
            return default

        return data

    async def update_settings_entry(self, discord_id: int, **kwargs) -> Optional[dict]:
        return await self.settings.find_one_and_update(
            {'discord_id': discord_id},
            {'$set': kwargs},
            return_document=ReturnDocument.AFTER,
            session=self._session
        )

    async def delete_settings_entry(self, discord_id: int) -> Optional[dict]:
        return await self.settings.find_one_and_delete(
            {'discord_id': discord_id},
            session=self._session
        )

    @staticmethod
    def _default_userdata(discord_id: int):
        return {
            'discord_id': discord_id,
            'premium': False,
            'blacklisted': False
        }

    async def search_userdata_entry(self, discord_id: int) -> dict:
        data = await self.userdata.find_one({'discord_id': discord_id}, session=self._session)

        if data is None:
            default = self._default_userdata(discord_id)
            await self.userdata.insert_one(default, session=self._session)
            return default

        return data

    async def update_userdata_entry(self, discord_id: int, **kwargs) -> Optional[dict]:
        return await self.userdata.find_one_and_update(
            {'discord_id': discord_id},
            {'$set': kwargs},
            return_document=ReturnDocument.AFTER,
            session=self._session
        )

    async def delete_userdata_entry(self, discord_id: int) -> Optional[dict]:
        return await self.userdata.find_one_and_delete(
            {'discord_id': discord_id},
            session=self._session
        )
