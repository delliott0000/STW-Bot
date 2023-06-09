from discord import app_commands, Interaction

from main import STWBot
from core.errors import STWException
from core.fortnite import Schematic
from components.embed import EmbedField
from components.decorators import is_not_blacklisted, is_logged_in, non_premium_cooldown
from components.paginator import Paginator
from components.itemselect import RecycleSelectionMenu, UpgradeSelectionMenu
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
                name=f'{schematic.emoji} {schematic.name}',
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

    @non_premium_cooldown()
    @is_logged_in()
    @is_not_blacklisted()
    @app_commands.describe(display='Epic account display name.', name='Name of the schematic.')
    @app_commands.command(name='list', description='View your own or another player\'s schematics.')
    async def list(self, interaction: Interaction, name: str = '', display: str = None):
        await interaction.response.defer(thinking=True, ephemeral=True)

        auth = self.bot.get_auth_session(interaction.user.id)
        account = await auth.get_other_account(display=display) if display is not None else await auth.get_own_account()
        schematics = [schematic for schematic in await account.schematics() if name.lower() in schematic.name.lower()]

        if not schematics:
            raise STWException(f'Schematic `{name}` not found.')

        embed_fields = self.schematics_to_fields(schematics)
        embeds = self.bot.fields_to_embeds(
            interaction,
            embed_fields,
            description=f'**IGN:** `{account.display}`',
            author_name='All Schematics',
            author_icon=await account.icon_url()
        )

        await interaction.followup.send(embed=embeds[0], view=Paginator(interaction, embeds))

    @non_premium_cooldown()
    @is_logged_in()
    @is_not_blacklisted()
    @app_commands.describe(
        name='Name of the schematic.',
        level='The desired level of the schematic.',
        material='The desired upgrade path of the schematic (if applicable).')
    @app_commands.choices(material=[
        app_commands.Choice(name='Ore', value='Ore'),
        app_commands.Choice(name='Crystal', value='Crystal')])
    @app_commands.command(name='upgrade', description='Upgrade one of your schematics.')
    async def upgrade(
            self,
            interaction: Interaction,
            name: str = '',
            level: int = 50,
            material: app_commands.Choice[str] = None
    ):
        await interaction.response.defer(thinking=True, ephemeral=True)

        if level not in range(2, 61):
            raise STWException(f'Level `{level}` is invalid, please try again.')

        account = await self.bot.get_full_account(interaction.user.id)
        schematics = [schematic for schematic in await account.schematics() if name.lower() in schematic.name.lower()]

        if not schematics:
            raise STWException(f'Schematic `{name}` not found.')

        embed_fields = self.schematics_to_fields(schematics)
        embeds = self.bot.fields_to_embeds(
            interaction,
            embed_fields,
            description=interaction.user.mention,
            author_name='Upgrade Schematics',
            author_icon=await account.icon_url()
        )

        view = Paginator(interaction, embeds)
        # noinspection PyTypeChecker
        view.add_item(UpgradeSelectionMenu(
            self.bot,
            interaction.command,
            schematics,
            level,
            material=material.name if material else 'Crystal'
        ))

        await interaction.followup.send(embed=embeds[0], view=view)

    @non_premium_cooldown()
    @is_logged_in()
    @is_not_blacklisted()
    @app_commands.describe(name='Name of the schematic.')
    @app_commands.command(name='recycle', description='Recycle one of your schematics.')
    async def recycle(self, interaction: Interaction, name: str = ''):
        await interaction.response.defer(thinking=True, ephemeral=True)

        account = await self.bot.get_full_account(interaction.user.id)
        schematics = [schematic for schematic in await account.schematics() if name.lower() in schematic.name.lower()]

        if not schematics:
            raise STWException(f'Schematic `{name}` not found.')

        embed_fields = self.schematics_to_fields(schematics)
        embeds = self.bot.fields_to_embeds(
            interaction,
            embed_fields,
            description=interaction.user.mention,
            author_name='Recycle Schematics',
            author_icon=await account.icon_url()
        )

        view = Paginator(interaction, embeds)
        # noinspection PyTypeChecker
        view.add_item(RecycleSelectionMenu(
            self.bot,
            interaction.command,
            schematics
        ))

        await interaction.followup.send(embed=embeds[0], view=view)


async def setup(bot: STWBot):
    bot.tree.add_command(SchematicCommands(bot))
