from discord import app_commands, Interaction

from main import STWBot
from core.fortnite import Schematic
from components.embed import EmbedField
from components.decorators import is_not_blacklisted, is_logged_in
from components.paginator import Paginator
from components.itemselect import RecycleSelectionMenu, UpgradeSelectionMenu, EvolveSelectionMenu
from resources.emojis import emojis


# noinspection PyUnresolvedReferences
class SchematicCommands(app_commands.Group):

    def __init__(
            self,
            bot: STWBot,
            name: str = 'schematic'
    ):
        super().__init__(name=name)
        self.bot = bot

    @staticmethod
    def schematics_to_fields(schematics: list[Schematic]) -> list[EmbedField]:
        embed_fields = []

        for schematic in schematics:

            perks = f'> {emojis["perk"]} **Perks:** ' \
                    f'{"".join([emojis["perk_rarities"][perk.rarity] for perk in schematic.perks])}\n' if \
                schematic.perks else ''

            embed_field = EmbedField(
                name=f'{emojis["rarities"][schematic.rarity]} {schematic.name}',
                value=f'> {emojis["level"]} **Level:** `{schematic.level}`\n'
                      f'> {emojis["tiers"][schematic.tier][schematic.material]} **Tier:** `{schematic.tier}`\n'
                      f'> {emojis["power"]} **PL:** `{schematic.power_level}`\n'
                      f'{perks}'
                      f'> {emojis["id"]} **Item ID:** `{schematic.item_id}`\n'
                      f'> {emojis["favourite"]} **Favorite:** '
                      f'{emojis["check" if schematic.favourite is True else "cross"]}'
            )

            embed_fields.append(embed_field)

        return embed_fields

    @app_commands.checks.cooldown(1, 15)
    @is_logged_in()
    @is_not_blacklisted()
    @app_commands.describe(display='Epic account display name.', name='Name of the schematic.')
    @app_commands.command(name='list', description='View your own or another player\'s schematics.')
    async def list(self, interaction: Interaction, display: str = None, name: str = ''):
        await interaction.response.defer(thinking=True, ephemeral=True)

        auth = self.bot.get_auth_session(interaction.user.id)
        account = await auth.get_other_account(display=display) if display is not None else await auth.get_own_account()
        schematics = [schematic for schematic in await account.schematics() if name.lower() in schematic.name.lower()]
        embed_fields = self.schematics_to_fields(schematics)

        embeds = self.bot.fields_to_embeds(
            interaction,
            embed_fields,
            description=f'**IGN:** `{account.display}`',
            author_name='All Schematics',
            author_icon=await account.icon_url()
        )

        await interaction.followup.send(embed=embeds[0], view=Paginator(interaction, embeds))

    @app_commands.checks.cooldown(1, 15)
    @is_logged_in()
    @is_not_blacklisted()
    @app_commands.describe(name='Name of the schematic.', increment='The desired increase in schematic level.')
    @app_commands.command(name='upgrade', description='Upgrade one of your schematics.')
    async def upgrade(self, interaction: Interaction, name: str = '', increment: int = 10):
        await interaction.response.defer(thinking=True, ephemeral=True)

        auth = self.bot.get_auth_session(interaction.user.id)
        account = await auth.get_own_account()
        schematics = [schematic for schematic in await account.schematics() if name.lower() in schematic.name.lower()]
        embed_fields = self.schematics_to_fields(schematics)

        embeds = self.bot.fields_to_embeds(
            interaction,
            embed_fields,
            description=interaction.user.mention,
            author_name='Upgrade Schematics',
            author_icon=await account.icon_url()
        )

        view = Paginator(interaction, embeds)
        view.add_item(UpgradeSelectionMenu(self.bot, schematics, increment=increment))

        await interaction.followup.send(embed=embeds[0], view=view)

    @app_commands.checks.cooldown(1, 15)
    @is_logged_in()
    @is_not_blacklisted()
    @app_commands.describe(name='Name of the schematic.', material='The desired upgrade path of the schematic.')
    @app_commands.choices(material=[
        app_commands.Choice(name='Ore', value='Ore'),
        app_commands.Choice(name='Crystal', value='Crystal')])
    @app_commands.command(name='evolve', description='Evolve one of your schematics.')
    async def evolve(self, interaction: Interaction, name: str = '', material: app_commands.Choice[str] = None):
        await interaction.response.defer(thinking=True, ephemeral=True)

        auth = self.bot.get_auth_session(interaction.user.id)
        account = await auth.get_own_account()
        schematics = [schematic for schematic in await account.schematics() if name.lower() in schematic.name.lower()]
        embed_fields = self.schematics_to_fields(schematics)

        embeds = self.bot.fields_to_embeds(
            interaction,
            embed_fields,
            description=interaction.user.mention,
            author_name='Evolve Schematics',
            author_icon=await account.icon_url()
        )

        view = Paginator(interaction, embeds)
        view.add_item(EvolveSelectionMenu(self.bot, schematics, material='' if material is None else material.name))

        await interaction.followup.send(embed=embeds[0], view=view)

    @app_commands.checks.cooldown(1, 15)
    @is_logged_in()
    @is_not_blacklisted()
    @app_commands.describe(name='Name of the schematic.')
    @app_commands.command(name='recycle', description='Recycle one of your schematics.')
    async def recycle(self, interaction: Interaction, name: str = ''):
        await interaction.response.defer(thinking=True, ephemeral=True)

        auth = self.bot.get_auth_session(interaction.user.id)
        account = await auth.get_own_account()
        schematics = [schematic for schematic in await account.schematics() if name.lower() in schematic.name.lower()]
        embed_fields = self.schematics_to_fields(schematics)

        embeds = self.bot.fields_to_embeds(
            interaction,
            embed_fields,
            description=interaction.user.mention,
            author_name='Recycle Schematics',
            author_icon=await account.icon_url()
        )

        view = Paginator(interaction, embeds)
        view.add_item(RecycleSelectionMenu(self.bot, schematics))

        await interaction.followup.send(embed=embeds[0], view=view)


async def setup(bot: STWBot):
    bot.tree.add_command(SchematicCommands(bot))
