from motor.motor_asyncio import AsyncIOMotorClient


class MongoDBClient:

    """
    Responsible for handling all MongoDB operations.

    This class should only be instantiated once during runtime.
    """

    def __init__(self, connection_uri: str):
        self.database = AsyncIOMotorClient(connection_uri).database

    # # # # # # # # # # # # # # # # #
    # USER SETTINGS
    # - - - - - - - - - - - - - - - -
    # stay_signed_in:   bool = True
    # auto_daily:       bool = False
    # -----planned-----
    # auto_research:    bool = False
    # auto_free_llamas: bool = False
    # # # # # # # # # # # # # # # # #

    @staticmethod
    def _default_settings(discord_id: int) -> dict:
        return {'_id': None, 'discord_id': discord_id, 'stay_signed_in': True, 'auto_daily': False}

    async def search_settings_entry(self, discord_id: int) -> dict:
        return await self.database.settings.find_one({'discord_id': discord_id}) or self._default_settings(discord_id)

    async def insert_settings_entry(self, **kwargs) -> None:
        await self.database.settings.insert_one(kwargs)

    async def edit_settings_entry(self, discord_id: int, **kwargs) -> dict:
        await self.database.settings.update_one({'discord_id': discord_id}, {'$set': kwargs})
        return await self.search_settings_entry(discord_id)

    async def delete_settings_entry(self, discord_id: int) -> None:
        await self.database.settings.delete_one({'discord_id': discord_id})

    # # # # # # # # # # # # # # # # #
    # USER DATA
    # - - - - - - - - - - - - - - - -
    # is_premium:       bool = False
    # is_blacklisted:   bool = False
    # # # # # # # # # # # # # # # # #

    @staticmethod
    def _default_data(discord_id: int):
        return {'_id': None, 'discord_id': discord_id, 'is_premium': False, 'is_blacklisted': False}

    async def search_data_entry(self, discord_id: int) -> dict:
        return await self.database.data.find_one({'discord_id': discord_id}) or self._default_data(discord_id)

    async def insert_data_entry(self, **kwargs) -> None:
        await self.database.data.insert_one(kwargs)

    async def edit_data_entry(self, discord_id: int, **kwargs) -> dict:
        await self.database.data.update_one({'discord_id': discord_id}, {'$set': kwargs})
        return await self.search_data_entry(discord_id)

    async def delete_data_entry(self, discord_id: int) -> None:
        await self.database.data.delete_one({'discord_id': discord_id})
