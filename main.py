import logging
import asyncio
import os
from aiohttp import ClientSession
from typing import Union, Dict
from math import floor
from datetime import timedelta
from time import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

try:
    from discord.ext import commands, tasks
    from discord import (
        __version__ as __discord__,
        Intents,
        app_commands,
        Interaction,
        LoginFailure,
        PrivilegedIntentsRequired,
        InteractionResponded,
        Guild,
        Color
    )

    # local imports
    from core.api import EpicGamesClient, AuthSession
    from core.errors import Unauthorized
    from core.mongo import MongoDBClient
    from core.accounts import FullEpicAccount, FriendEpicAccount, PartialEpicAccount
    from components.embed import CustomEmbed, EmbedField
    from resources import config
except ModuleNotFoundError as unknown_import:
    logging.fatal(f'Missing required dependencies - {unknown_import}.')
    exit(0)


class STWBot(commands.Bot):

    def __init__(self):

        intents = Intents.none()
        intents.guilds = True

        super().__init__(
            command_prefix=None,
            intents=intents,
            help_command=None,
            owner_ids=config.OWNERS
        )
        # Redefined in `async setup_hook`
        self._session = None
        self.epic_api = None

        self.mongo_db = MongoDBClient(config.MONGO)

        self.app_commands = []
        self.tree.on_error = self.app_command_error

        self._cached_auth_sessions: Dict[int, AuthSession] = {}

    @staticmethod
    def color(guild: Guild):
        try:
            return guild.me.colour
        except AttributeError:
            return 0xffffff

    @staticmethod
    async def basic_response(interaction: Interaction, message: str, color: int = None) -> None:
        basic_embed = CustomEmbed(interaction, description=message, color=color)
        try:
            # noinspection PyUnresolvedReferences
            await interaction.response.send_message(embed=basic_embed, ephemeral=True)
        except InteractionResponded:
            await interaction.followup.send(embed=basic_embed)

    async def bad_response(self, interaction: Interaction, message: str) -> None:
        await self.basic_response(interaction, f'❌ {message}', Color.red())

    @staticmethod
    def fields_to_embeds(
            interaction: Interaction,
            fields: list[EmbedField],
            title: str = None,
            description: str = None,
            author_name: str = None,
            author_icon: str = None
    ) -> list[CustomEmbed]:
        embed_list = [CustomEmbed(
            interaction,
            title=title,
            description=description
        )]

        for field in fields:

            if len(embed_list[-1].fields) > 5:
                embed_list.append(CustomEmbed(
                    interaction,
                    title=title,
                    description=description
                ))

            embed_list[-1].append_field(field)

        for embed in embed_list:
            embed.set_author(name=author_name, icon_url=author_icon)
            embed.set_footer(text=f'Page {embed_list.index(embed) + 1} of {len(embed_list)}')

        return embed_list

    def get_auth_session(self, discord_id: int) -> Union[AuthSession, None]:
        return self._cached_auth_sessions.get(discord_id)

    def discord_id_from_partial(self, account: Union[PartialEpicAccount, FriendEpicAccount]) -> Union[int, None]:
        for discord_id in self._cached_auth_sessions:
            if self._cached_auth_sessions[discord_id].epic_id == account.id:
                return discord_id

    # Simple shortcut method that attempts to call `async AuthSession.get_own_account()`
    async def get_full_account(self, discord_id: int) -> Union[FullEpicAccount, None]:
        auth_session = self.get_auth_session(discord_id)
        try:
            epic_account = await auth_session.get_own_account()
            return epic_account
        except AttributeError:
            return None

    def add_auth_session(self, auth_session: AuthSession) -> None:
        self._cached_auth_sessions[auth_session.discord_id] = auth_session

    async def del_auth_session(self, discord_id: int) -> None:
        auth_session = self._cached_auth_sessions.get(discord_id)

        if not isinstance(auth_session, AuthSession):
            return

        try:
            await auth_session.kill()
        except Unauthorized:
            pass

        self._cached_auth_sessions.pop(discord_id)

    def user_is_logged_in(self, discord_id: int) -> bool:
        return True if isinstance(self.get_auth_session(discord_id), AuthSession) else False

    async def user_is_blacklisted(self, discord_id: int) -> bool:
        return (await self.mongo_db.search_data_entry(discord_id))['is_blacklisted']

    async def user_is_premium(self, discord_id: int) -> bool:
        return (await self.mongo_db.search_data_entry(discord_id))['is_premium']

    async def user_setting_stay_logged_in(self, discord_id: int) -> bool:
        return (await self.mongo_db.search_settings_entry(discord_id))['stay_signed_in']

    async def user_setting_auto_daily(self, discord_id: int) -> bool:
        return (await self.mongo_db.search_data_entry(discord_id))['auto_daily']

    async def app_command_error(self, interaction: Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandOnCooldown):
            message = f'You\'re on cooldown. Try again in `{timedelta(seconds=floor(error.retry_after))}`.'

        elif isinstance(error, app_commands.CommandInvokeError):
            message = str(error.original)

        else:
            message = str(error)

        await self.bad_response(interaction, message)

    @tasks.loop(minutes=1)
    async def renew_sessions(self):
        for discord_id in self._cached_auth_sessions:
            if await self.user_setting_stay_logged_in(discord_id) is False:
                continue

            auth_session = self._cached_auth_sessions[discord_id]
            if auth_session.refresh_expires_at - time() < 120:
                try:
                    logging.info(f'Attempting to renew OAuth session {auth_session.access_token}...')
                    await auth_session.renew()
                    logging.info(f'Success.')
                except Unauthorized:
                    logging.error(f'Failed to renew OAuth session {auth_session.access_token} - ending session...')
                    await self.del_auth_session(discord_id)

    async def setup_hook(self):
        logging.info(f'Logging in as {self.user} (ID: {self.user.id})...')
        logging.info(f'Owners: {", ".join([str(await self.fetch_user(user_id)) for user_id in self.owner_ids])}')

        self._session = ClientSession()
        self.epic_api = EpicGamesClient(self._session)

        logging.info('Syncing app commands...')
        self.app_commands = await self.tree.sync()
        logging.info('Done!')

        self.renew_sessions.start()

    def run_bot(self):

        async def _bot_runner():
            for filename in os.listdir('./ext'):
                if filename.endswith('.py'):
                    try:
                        await self.load_extension(f'ext.{filename[:-3]}')
                    except (commands.ExtensionFailed, commands.NoEntryPointError) as err:
                        logging.error(f'Extension {filename} could not be loaded: {err}')
            try:
                await self.start(config.TOKEN)
            except LoginFailure:
                logging.fatal('Invalid token passed.')
            except PrivilegedIntentsRequired:
                logging.fatal('Intents are being requested that have not been enabled in the developer portal.')

        async def _cleanup():
            # noinspection PyBroadException
            try:
                await self._session.close()
            except Exception:
                pass
            self.renew_sessions.stop()

        try:
            asyncio.run(_bot_runner())
        except (KeyboardInterrupt, SystemExit):
            logging.info('Received signal to terminate bot and event loop.')
        finally:
            logging.info('Cleaning up tasks and connections...')
            asyncio.run(_cleanup())
            logging.info('Done. Have a nice day!')


if __name__ == '__main__':

    if __discord__ == '2.2.3':
        bot = STWBot()
        bot.run_bot()

    else:
        logging.fatal('The incorrect version of discord.py has been installed.')
        logging.fatal('Current Version: {}'.format(__discord__))
        logging.fatal('Required: 2.2.3')
