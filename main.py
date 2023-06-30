import logging
import asyncio
import os
from aiohttp import ClientSession
from typing import Union, Dict, Optional
from math import floor
from datetime import timedelta
from time import time as t_time
from datetime import time as dt_time
from traceback import format_exception

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

try:
    from discord.ext import commands, tasks
    from discord.utils import MISSING
    from discord.ui import View
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
    from core.errors import Unauthorized, HTTPException
    from core.mongo import MongoDBClient
    from core.accounts import FullEpicAccount, FriendEpicAccount, PartialEpicAccount
    from core.fortnite import MissionAlert
    from components.embed import CustomEmbed, EmbedField
    from components.traceback import TracebackView
    from resources.lookup import stringList
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
        # Redefined later on
        self._session = self.epic_api = self.mongo_db = None

        self.app_commands = []
        self.tree.on_error = self.app_command_error

        self._cached_auth_sessions: Dict[int, AuthSession] = {}

        self._mission_alert_cache = []
        self._fnc_base_url = 'https://fortnitecentral.genxgames.gg/api/v1/export?path='
        self._all_theaters = '/Game/Balance/DataTables/GameDifficultyGrowthBounds.GameDifficultyGrowthBounds'

    @staticmethod
    def color(guild: Guild) -> Union[Color, int]:
        try:
            return guild.me.color
        except AttributeError:
            return 0xffffff

    @staticmethod
    async def basic_response(interaction: Interaction, message: str, color: int = None, view: View = MISSING) -> None:
        basic_embed = CustomEmbed(interaction, description=message, color=color)
        try:
            # noinspection PyUnresolvedReferences
            await interaction.response.send_message(embed=basic_embed, view=view, ephemeral=True)
        except InteractionResponded:
            await interaction.followup.send(embed=basic_embed, view=view)

    async def bad_response(self, interaction: Interaction, message: str, view: View = MISSING) -> None:
        await self.basic_response(interaction, f'❌ {message}', Color.red(), view=view)

    @staticmethod
    def fields_to_embeds(
            interaction: Interaction,
            fields: list[EmbedField],
            field_limit: int = 6,
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

            if len(embed_list[-1].fields) > field_limit - 1:
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

    def get_auth_session(self, discord_id: int) -> Optional[AuthSession]:
        return self._cached_auth_sessions.get(discord_id)

    def discord_id_from_partial(self, account: Union[PartialEpicAccount, FriendEpicAccount]) -> Optional[int]:
        for discord_id in self._cached_auth_sessions:
            if self._cached_auth_sessions[discord_id].epic_id == account.id:
                return discord_id

    async def get_full_account(self, discord_id: int) -> Optional[FullEpicAccount]:
        auth_session = self.get_auth_session(discord_id)
        try:
            return await auth_session.get_own_account()
        except AttributeError:
            return None

    def add_auth_session(self, auth_session: AuthSession) -> None:
        self._cached_auth_sessions[auth_session.discord_id] = auth_session

    async def del_auth_session(self, discord_id: int) -> None:
        # noinspection PyBroadException
        try:
            await self._cached_auth_sessions.get(discord_id).kill()
        except Exception:
            pass

        self._cached_auth_sessions.pop(discord_id)

    def user_is_logged_in(self, discord_id: int) -> bool:
        return True if isinstance(self.get_auth_session(discord_id), AuthSession) else False

    async def user_is_blacklisted(self, discord_id: int) -> bool:
        return (await self.mongo_db.search_userdata_entry(discord_id)).get('blacklisted', False)

    async def user_is_premium(self, discord_id: int) -> bool:
        return (await self.mongo_db.search_userdata_entry(discord_id)).get('premium', False)

    async def user_setting_stay_signed_in(self, discord_id: int) -> bool:
        return (await self.mongo_db.search_settings_entry(discord_id)).get('stay_signed_in', True)

    async def app_command_error(self, interaction: Interaction, error: app_commands.AppCommandError) -> None:
        if isinstance(error, app_commands.CommandOnCooldown):
            message = f'You\'re on cooldown. Try again in `{timedelta(seconds=floor(error.retry_after))}`.'

        elif isinstance(error, app_commands.CommandInvokeError):
            message = str(error.original)

        else:
            message = str(error)

        traceback_ = f'**Full Traceback:**\n' \
                     f'```\n{"".join(format_exception(type(error), error, error.__traceback__))}\n```'
        view = TracebackView(self, interaction, traceback=traceback_)

        await self.bad_response(interaction, message, view=view)

    @tasks.loop(minutes=1)
    async def manage_sessions(self) -> None:
        for discord_id in self._cached_auth_sessions:

            auth = self.get_auth_session(discord_id)

            if auth.refresh_expires_at - t_time() < 120 and await self.user_setting_stay_signed_in(discord_id) is True:
                logging.info(f'Attempting to renew Auth session {auth.access_token}...')
                try:
                    await auth.renew()
                    logging.info(f'Success.')
                except Unauthorized:
                    logging.error(f'Failed to renew Auth session {auth.access_token} - ending session...')
                    await self.del_auth_session(discord_id)

            elif auth.cache_is_expired is True:
                auth.del_own_account()

    async def missions(self) -> list[MissionAlert]:
        if not self._mission_alert_cache:
            await self.refresh_mission_alerts()
        return self._mission_alert_cache

    @tasks.loop(time=dt_time(minute=1))
    async def refresh_mission_alerts(self) -> None:
        self._mission_alert_cache = []

        logging.info('Attempting to refresh mission alert data...')

        for discord_id in self._cached_auth_sessions:
            auth_session = self._cached_auth_sessions[discord_id]
            try:
                data = await auth_session.get_mission_data()
                break
            except HTTPException:
                continue
        else:
            logging.error('Unable to retrieve today\'s mission data, cancelling...')
            return

        theaters = data.get('theaters')
        missions = data.get('missions')
        alerts = data.get('missionAlerts')

        theater_data = await self._session.get(self._fnc_base_url + self._all_theaters)
        theater_json = await theater_data.json()

        async def _add_mission(i: int, theater: dict):

            theater_id = theater.get('theaterId')
            for _theater in theaters:
                if _theater.get('uniqueId') == theater_id:
                    theater_name = _theater.get('displayName').get('en')
                    break
            else:
                theater_name = 'Unknown Theater'

            for available_alert in theater.get("availableMissionAlerts"):

                tile_index = available_alert.get('tileIndex')
                alert_rewards = available_alert.get('missionAlertRewards', {}).get('items', [])

                tile_theme_path = data['theaters'][i]['tiles'][tile_index]['zoneTheme']
                tile_theme_file = await self._session.get(self._fnc_base_url + tile_theme_path.split('.')[0])
                tile_theme_json = await tile_theme_file.json()

                try:
                    tile_theme_name = tile_theme_json['jsonOutput'][1]['Properties']['ZoneName']['sourceString']
                except KeyError:
                    tile_theme_name = 'Unknown'

                for mission in missions[i].get('availableMissions'):
                    if mission.get('tileIndex') == tile_index:

                        __theater = mission.get('missionDifficultyInfo').get("rowName")
                        generator = mission.get('missionGenerator')

                        for mission_name in stringList['Missions']:
                            if mission_name in generator:
                                name = stringList['Missions'][mission_name]
                                break
                        else:
                            name = 'Unknown Mission'

                        try:
                            power = \
                                theater_json['jsonOutput'][0]['Rows'][__theater]['ThreatDisplayName']['sourceString']
                        except KeyError:
                            power = '0'

                        self._mission_alert_cache.append(MissionAlert(
                            name=name,
                            power=power,
                            theater=theater_name,
                            tile_theme=tile_theme_name,
                            alert_rewards_data=alert_rewards
                        ))

                        break

        add_mission_tasks = [asyncio.ensure_future(_add_mission(i, theater)) for i, theater in enumerate(alerts)]
        await asyncio.gather(*add_mission_tasks)

        logging.info('Success!')

    async def setup_hook(self) -> None:
        logging.info(f'Logging in as {self.user} (ID: {self.user.id})...')
        logging.info(f'Owners: {", ".join([(await self.fetch_user(user_id)).name for user_id in self.owner_ids])}')

        self._session = ClientSession()
        self.epic_api = EpicGamesClient(self._session)

        logging.info('Syncing app commands...')
        self.app_commands = await self.tree.sync()
        logging.info('Done!')

        self.manage_sessions.start()
        self.refresh_mission_alerts.start()

    def run_bot(self) -> None:

        async def _run_bot():
            async with self, MongoDBClient(config.MONGO) as self.mongo_db:
                for filename in os.listdir('./ext'):
                    if filename.endswith('.py'):
                        try:
                            await self.load_extension(f'ext.{filename[:-3]}')
                        except (commands.ExtensionFailed, commands.NoEntryPointError) as extension_error:
                            logging.error(f'Extension {filename} could not be loaded: {extension_error}')
                try:
                    await self.start(config.TOKEN)
                except LoginFailure:
                    logging.fatal('Invalid token passed.')
                except PrivilegedIntentsRequired:
                    logging.fatal('Intents are being requested that have not been enabled in the developer portal.')

        async def _cleanup():
            self.manage_sessions.cancel()
            self.refresh_mission_alerts.cancel()

            kill_session_tasks = []

            for auth_session in self._cached_auth_sessions.values():
                kill_session_tasks.append(asyncio.ensure_future(auth_session.kill()))

            await asyncio.gather(*kill_session_tasks)

            if self._session:
                await self._session.close()

        # noinspection PyUnresolvedReferences
        with asyncio.Runner() as runner:
            try:
                runner.run(_run_bot())
            except (KeyboardInterrupt, SystemExit):
                logging.info('Received signal to terminate bot and event loop.')
            finally:
                logging.info('Cleaning up tasks and connections...')
                runner.run(_cleanup())
                logging.info('Done. Have a nice day!')


if __name__ == '__main__':

    if __discord__ == '2.3.1':
        bot = STWBot()
        bot.run_bot()

    else:
        logging.fatal('The incorrect version of discord.py has been installed.')
        logging.fatal('Current Version: {}'.format(__discord__))
        logging.fatal('Required: 2.3.1')
