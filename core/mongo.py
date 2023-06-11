from motor.motor_asyncio import AsyncIOMotorClient


class MongoDBClient:

    """
    Responsible for handling all MongoDB operations.

    This class should only be instantiated once during runtime.
    """

    def __init__(self, connection_uri: str):
        self.database = AsyncIOMotorClient(connection_uri).database

    @staticmethod
    def _default_settings(discord_id: int) -> dict:
        return {
            'discord_id': discord_id,
            'stay_signed_in': True,
            'auto_daily': False,
            'auto_research': False,
            'auto_free_llamas': False
        }

    async def search_settings_entry(self, discord_id: int) -> dict:
        data = await self.database.settings.find_one({'discord_id': discord_id})

        if data is None:
            await self.database.settings.insert_one(self._default_settings(discord_id))
            return await self.search_settings_entry(discord_id)

        return data

    async def edit_settings_entry(self, discord_id: int, **kwargs) -> dict:
        await self.database.settings.update_one({'discord_id': discord_id}, {'$set': kwargs})

        return await self.search_settings_entry(discord_id)

    async def delete_settings_entry(self, discord_id: int) -> dict:
        data = await self.search_settings_entry(discord_id)

        await self.database.settings.delete_one({'discord_id': discord_id})

        return data

    @staticmethod
    def _default_data(discord_id: int):
        return {
            'discord_id': discord_id,
            'is_premium': False,
            'is_blacklisted': False
        }

    async def search_data_entry(self, discord_id: int) -> dict:
        data = await self.database.data.find_one({'discord_id': discord_id})

        if data is None:
            await self.database.data.insert_one(self._default_data(discord_id))
            return await self.search_data_entry(discord_id)

        return data

    async def edit_data_entry(self, discord_id: int, **kwargs) -> dict:
        await self.database.data.update_one({'discord_id': discord_id}, {'$set': kwargs})

        return await self.search_data_entry(discord_id)

    async def delete_data_entry(self, discord_id: int) -> dict:
        data = await self.search_data_entry(discord_id)

        await self.database.data.delete_one({'discord_id': discord_id})

        return data
