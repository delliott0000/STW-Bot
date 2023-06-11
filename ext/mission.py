from typing import Optional

from discord import app_commands, Interaction

from main import STWBot
from core.fortnite import MissionAlert
from components.embed import EmbedField
from components.decorators import is_not_blacklisted, is_logged_in, non_premium_cooldown
from components.paginator import Paginator
from resources.emojis import emojis


# noinspection PyUnresolvedReferences
class MissionCommands(app_commands.Group):

    def __init__(
            self,
            bot: STWBot,
            name: str = 'missions'
    ):
        super().__init__(name=name)
        self.bot = bot
        self.theater_list = ['Stonewood', 'Plankerton', 'Canny Valley', 'Twine Peaks']

    @staticmethod
    def missions_to_fields(missions: list[MissionAlert], include_theater: bool = False) -> list[EmbedField]:
        embed_fields = []

        for mission in missions:

            rewards_str = '\n'.join(
                [f'> {reward.emoji} `{reward.name} x{reward.quantity}`' for reward in mission.alert_rewards])
            theater_str = f"({mission.theater})" if include_theater is True else ""

            embed_field = EmbedField(
                name=f'{emojis["mission_icons"][mission.name]} {mission.name} {theater_str}',
                value=f'> {emojis["power"]} **Power Rating:** `{mission.power}`\n'
                      f'> {emojis["tile_theme"]} **Zone Theme:** `{mission.tile_theme}`\n'
                      f'> {emojis["red_skull"]} **4-Player:** '
                      f'{emojis["check"] if mission.four_player is True else emojis["cross"]}\n'
                      f'> {emojis["loot"]} **Alert Rewards:**\n{rewards_str}'
            )

            embed_fields.append(embed_field)

        return embed_fields

    def order_theaters(self, theaters: set[Optional[str]]):
        ordered_list = []

        for item in self.theater_list:
            if item in theaters:
                ordered_list.append(item)
        for item in theaters:
            if item not in self.theater_list:
                ordered_list.append(item)

        return ordered_list

    @non_premium_cooldown()
    @is_logged_in()
    @is_not_blacklisted()
    @app_commands.describe(theater='Choose a specific zone (e.g. Twine Peaks) to view.')
    @app_commands.choices(theater=[
        app_commands.Choice(name='Stonewood', value='Stonewood'),
        app_commands.Choice(name='Plankerton', value='Plankerton'),
        app_commands.Choice(name='Canny Valley', value='Canny Valley'),
        app_commands.Choice(name='Twine Peaks', value='Twine Peaks'),
        app_commands.Choice(name='Ventures', value='Ventures')])
    @app_commands.command(name='alert', description='View all of today\'s mission alerts.')
    async def alert(self, interaction: Interaction, theater: app_commands.Choice[str] = None):
        await interaction.response.defer(thinking=True, ephemeral=True)

        missions = await self.bot.missions()

        if theater is None:
            pass
        elif theater.name == 'Ventures':
            missions = [mission for mission in missions if mission.theater not in self.theater_list]
        else:
            missions = [mission for mission in missions if mission.theater == theater.name]

        # Chunk missions based on theater name to produce a chapter-like effect in our embed pages
        embed_list = []
        theater_list = self.order_theaters(set(mission.theater for mission in missions))
        for theater in theater_list:

            theater_missions = [mission for mission in missions if mission.theater == theater]
            theater_missions.sort(key=lambda m: m.power)

            embed_fields = self.missions_to_fields(theater_missions)
            embeds = self.bot.fields_to_embeds(
                interaction,
                embed_fields,
                field_limit=4,
                description=f'**Theater:** `{theater}`',
                author_name='Mission Alerts',
                author_icon=self.bot.user.avatar
            )
            embed_list += embeds

        # Correcting the displayed page numbers
        for embed in embed_list:
            embed.set_footer(text=f'Page {embed_list.index(embed) + 1} of {len(embed_list)}')

        await interaction.followup.send(embed=embed_list[0], view=Paginator(interaction, embed_list))

    @non_premium_cooldown()
    @is_logged_in()
    @is_not_blacklisted()
    @app_commands.command(name='vbucks', description='View today\'s VBuck mission alerts.')
    async def vbucks(self, interaction: Interaction):
        await interaction.response.defer(thinking=True, ephemeral=True)

        missions = await self.bot.missions()

        vbuck_missions = []
        vbuck_count = 0

        for mission in missions:
            for reward in mission.alert_rewards:
                if reward.name == 'VBucks':
                    vbuck_missions.append(mission)
                    vbuck_count += reward.quantity
                    break

        fields = self.missions_to_fields(vbuck_missions, include_theater=True)
        embeds = self.bot.fields_to_embeds(
            interaction,
            fields,
            field_limit=4,
            description=f'**Total VBucks:** `{vbuck_count}`',
            author_name='VBuck Alerts',
            author_icon=emojis['vbuck_url']
        )

        await interaction.followup.send(embed=embeds[0], view=Paginator(interaction, embeds))

    @non_premium_cooldown()
    @is_logged_in()
    @is_not_blacklisted()
    @app_commands.command(name='survivors', description='View today\'s legendary/mythic survivor mission alerts.')
    async def survivors(self, interaction: Interaction):
        await interaction.response.defer(thinking=True, ephemeral=True)

        missions = await self.bot.missions()

        leg_surv_missions = []

        for mission in missions:
            for reward in mission.alert_rewards:
                if (reward.name == 'Survivor' and reward.rarity == 'legendary') or reward.rarity == 'mythic':
                    leg_surv_missions.append(mission)
                    break

        fields = self.missions_to_fields(leg_surv_missions, include_theater=True)
        embeds = self.bot.fields_to_embeds(
            interaction,
            fields,
            field_limit=4,
            description=f'**Total Missions:** `{len(leg_surv_missions)}`',
            author_name='Legendary Survivor Alerts',
            author_icon=emojis['survivor_url']
        )

        await interaction.followup.send(embed=embeds[0], view=Paginator(interaction, embeds))


async def setup(bot: STWBot):
    bot.tree.add_command(MissionCommands(bot))
