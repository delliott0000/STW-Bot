from typing import Union

from discord import app_commands, Interaction

from main import STWBot
from core.fortnite import Survivor, LeadSurvivor
from components.embed import EmbedField, CustomEmbed
from components.decorators import is_not_blacklisted, is_logged_in
from components.itemselect import RecycleSelectionMenu, UpgradeSelectionMenu, EvolveSelectionMenu
from components.paginator import Paginator
from resources.emojis import emojis


# noinspection PyUnresolvedReferences
class SurvivorCommands(app_commands.Group):

    def __init__(
            self,
            bot: STWBot,
            name: str = 'survivor'
    ):
        super().__init__(name=name)
        self.bot = bot

    @app_commands.checks.cooldown(1, 15)
    @is_logged_in()
    @is_not_blacklisted()
    @app_commands.command(name='squads', description='View your own or another player\'s survivor squads.')
    async def squads(self, interaction: Interaction, display: str = None):
        await interaction.response.defer(thinking=True, ephemeral=True)

        auth = self.bot.get_auth_session(interaction.user.id)
        account = await auth.get_other_account(display=display) if display is not None else await auth.get_own_account()
        icon_url = await account.icon_url()
        squads = await account.survivor_squads()

        embed_list = []

        for squad in squads:

            squad_fort = squad.total_fort_stats
            fort_type = max(squad_fort, key=squad_fort.get)
            points = squad_fort[fort_type]

            squad_embed = CustomEmbed(
                interaction,
                description=f'**IGN:** `{account.display}`\n'
                            f'**{emojis["fort_icons"][fort_type]} {fort_type}:** `+{points}`\n'
            )
            squad_embed.set_author(name=squad.name, icon_url=icon_url)
            squad_embed.set_thumbnail(url=emojis['squads'][squad.name])

            if squad.lead is not None:
                lead_field = self.survivors_to_fields([squad.lead], show_ids=False)[0]
                squad_embed.append_field(lead_field)

            survivor_fields = self.survivors_to_fields(squad.survivors, show_ids=False)
            for field in survivor_fields:
                field.inline = True
                squad_embed.append_field(field)

            embed_list.append(squad_embed)

        for embed in embed_list:
            embed.set_footer(text=f'Page {embed_list.index(embed) + 1} of {len(embed_list)}')

        await interaction.followup.send(embed=embed_list[0], view=Paginator(interaction, embed_list))

    @staticmethod
    def survivors_to_fields(survivors: list[Union[Survivor, LeadSurvivor]], show_ids: bool = True) -> list[EmbedField]:
        embed_fields = []

        for survivor in survivors:

            extra_str = emojis["set_bonuses"][survivor.set_bonus_type] if isinstance(survivor, Survivor)\
                else emojis["lead_survivors"][survivor.preferred_squad_name]

            id_str = f'> {emojis["id"]} **Item ID:** `{survivor.item_id}`\n' if show_ids is True else ''

            embed_field = EmbedField(
                name=f'{emojis["rarities"][survivor.rarity]} '
                     f'{emojis["personalities"][survivor.personality]} '
                     f'{extra_str} '
                     f'{survivor.name}',
                value=f'> {emojis["level"]} **Level:** `{survivor.level}`\n'
                      f'> {emojis["tiers"][survivor.tier][None]} **Tier:** `{survivor.tier}`\n'
                      f'> {emojis["power"]} **PL:** `{survivor.base_power_level}`\n'
                      f'{id_str}'
                      f'> {emojis["favourite"]} **Favorite:** '
                      f'{emojis["check" if survivor.favourite is True else "cross"]}',
            )

            embed_fields.append(embed_field)

        return embed_fields

    @app_commands.checks.cooldown(1, 15)
    @is_logged_in()
    @is_not_blacklisted()
    @app_commands.describe(display='Epic account display name.', personality='Search for survivors by personality.')
    @app_commands.choices(personality=[app_commands.Choice(name=personality, value=personality) for personality in [
        'Curious', 'Dependable', 'Cooperative', 'Pragmatic', 'Adventurous', 'Competitive', 'Dreamer', 'Analytical'
    ]])
    @app_commands.command(name='list', description='View your own or another player\'s survivors.')
    async def list(self, interaction: Interaction, display: str = None, personality: app_commands.Choice[str] = None):
        await interaction.response.defer(thinking=True, ephemeral=True)

        auth = self.bot.get_auth_session(interaction.user.id)
        account = await auth.get_other_account(display=display) if display is not None else await auth.get_own_account()
        survivors = await account.survivors()

        if personality is not None:
            survivors = [survivor for survivor in survivors if survivor.personality == personality.value]

        embed_fields = self.survivors_to_fields(survivors)

        embeds = self.bot.fields_to_embeds(
            interaction,
            embed_fields,
            description=f'**IGN:** `{account.display}`',
            author_name='All Survivors',
            author_icon=await account.icon_url()
        )

        await interaction.followup.send(embed=embeds[0], view=Paginator(interaction, embeds))

    @app_commands.checks.cooldown(1, 15)
    @is_logged_in()
    @is_not_blacklisted()
    @app_commands.describe(personality='Personality of the survivor.', increment='Desired increase in survivor level.')
    @app_commands.choices(personality=[app_commands.Choice(name=personality, value=personality) for personality in [
        'Curious', 'Dependable', 'Cooperative', 'Pragmatic', 'Adventurous', 'Competitive', 'Dreamer', 'Analytical'
    ]])
    @app_commands.command(name='upgrade', description='Upgrade one of your survivors.')
    async def upgrade(self, inter: Interaction, personality: app_commands.Choice[str] = None, increment: int = 10):
        await inter.response.defer(thinking=True, ephemeral=True)

        auth = self.bot.get_auth_session(inter.user.id)
        account = await auth.get_own_account()
        survivors = await account.survivors()

        if personality is not None:
            survivors = [survivor for survivor in survivors if survivor.personality == personality.value]

        embed_fields = self.survivors_to_fields(survivors)

        embeds = self.bot.fields_to_embeds(
            inter,
            embed_fields,
            description=inter.user.mention,
            author_name='Upgrade Survivors',
            author_icon=await account.icon_url()
        )

        view = Paginator(inter, embeds)
        view.add_item(UpgradeSelectionMenu(self.bot, survivors, increment=increment))

        await inter.followup.send(embed=embeds[0], view=view)

    @app_commands.checks.cooldown(1, 15)
    @is_logged_in()
    @is_not_blacklisted()
    @app_commands.describe(personality='Personality of the survivor.')
    @app_commands.choices(personality=[app_commands.Choice(name=personality, value=personality) for personality in [
        'Curious', 'Dependable', 'Cooperative', 'Pragmatic', 'Adventurous', 'Competitive', 'Dreamer', 'Analytical'
    ]])
    @app_commands.command(name='evolve', description='Evolve one of your survivors.')
    async def evolve(self, interaction: Interaction, personality: app_commands.Choice[str] = None):
        await interaction.response.defer(thinking=True, ephemeral=True)

        auth = self.bot.get_auth_session(interaction.user.id)
        account = await auth.get_own_account()
        survivors = await account.survivors()

        if personality is not None:
            survivors = [survivor for survivor in survivors if survivor.personality == personality.value]

        embed_fields = self.survivors_to_fields(survivors)

        embeds = self.bot.fields_to_embeds(
            interaction,
            embed_fields,
            description=interaction.user.mention,
            author_name='Evolve Survivors',
            author_icon=await account.icon_url()
        )

        view = Paginator(interaction, embeds)
        view.add_item(EvolveSelectionMenu(self.bot, survivors))

        await interaction.followup.send(embed=embeds[0], view=view)

    @app_commands.checks.cooldown(1, 15)
    @is_logged_in()
    @is_not_blacklisted()
    @app_commands.describe(personality='Personality of the survivor.')
    @app_commands.choices(personality=[app_commands.Choice(name=personality, value=personality) for personality in [
        'Curious', 'Dependable', 'Cooperative', 'Pragmatic', 'Adventurous', 'Competitive', 'Dreamer', 'Analytical'
    ]])
    @app_commands.command(name='recycle', description='Recycle one of your survivors.')
    async def recycle(self, interaction: Interaction, personality: app_commands.Choice[str] = None):
        await interaction.response.defer(thinking=True, ephemeral=True)

        auth = self.bot.get_auth_session(interaction.user.id)
        account = await auth.get_own_account()
        survivors = await account.survivors()

        if personality is not None:
            survivors = [survivor for survivor in survivors if survivor.personality == personality.value]

        embed_fields = self.survivors_to_fields(survivors)

        embeds = self.bot.fields_to_embeds(
            interaction,
            embed_fields,
            description=interaction.user.mention,
            author_name='Recycle Survivors',
            author_icon=await account.icon_url()
        )

        view = Paginator(interaction, embeds)
        view.add_item(RecycleSelectionMenu(self.bot, survivors))

        await interaction.followup.send(embed=embeds[0], view=view)


async def setup(bot: STWBot):
    bot.tree.add_command(SurvivorCommands(bot))
