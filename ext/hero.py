from discord import app_commands, Interaction

from main import STWBot
from core.errors import STWException
from core.fortnite import Hero
from components.embed import EmbedField
from components.decorators import is_not_blacklisted, is_logged_in, non_premium_cooldown
from components.paginator import Paginator
from components.itemselect import RecycleSelectionMenu, UpgradeSelectionMenu
from resources.emojis import emojis


# noinspection PyUnresolvedReferences
class HeroCommands(app_commands.Group):

    def __init__(
            self,
            bot: STWBot,
            name: str = 'heroes'
    ):
        super().__init__(name=name)
        self.bot = bot

    @staticmethod
    def heroes_to_fields(heroes: list[Hero]) -> list[EmbedField]:
        embed_fields = []

        for hero in heroes:

            embed_field = EmbedField(
                name=f'{hero.emoji} {hero.name}',
                value=f'> {emojis["level"]} **Level:** `{hero.level}`\n'
                      f'> {emojis["tiers"][hero.tier][None]} **Tier:** `{hero.tier}`\n'
                      f'> {emojis["power"]} **PL:** `{hero.power_level}`\n'
                      f'> {emojis["id"]} **Item ID:** `{hero.item_id}`\n'
                      f'> {emojis["favourite"]} **Favorite:** '
                      f'{emojis["check" if hero.favourite is True else "cross"]}'
            )

            embed_fields.append(embed_field)

        return embed_fields

    @non_premium_cooldown()
    @is_logged_in()
    @is_not_blacklisted()
    @app_commands.describe(display='Epic account display name.', name='Name of the hero.')
    @app_commands.command(name='list', description='View your own or another player\'s heroes.')
    async def list(self, interaction: Interaction, name: str = '', display: str = None):
        await interaction.response.defer(thinking=True, ephemeral=True)

        auth = self.bot.get_auth_session(interaction.user.id)
        account = await auth.get_other_account(display=display) if display is not None else await auth.get_own_account()
        heroes = [hero for hero in await account.heroes() if name.lower() in hero.name.lower()]

        if not heroes:
            raise STWException(f'Hero `{name}` not found.')

        embed_fields = self.heroes_to_fields(heroes)
        embeds = self.bot.fields_to_embeds(
            interaction,
            embed_fields,
            description=f'**IGN:** `{account.display}`',
            author_name='All Heroes',
            author_icon=await account.icon_url()
        )

        await interaction.followup.send(embed=embeds[0], view=Paginator(interaction, embeds))

    @non_premium_cooldown()
    @is_logged_in()
    @is_not_blacklisted()
    @app_commands.describe(name='Name of the hero.', level='The desired level of the hero.')
    @app_commands.command(name='upgrade', description='Upgrade one of your heroes.')
    async def upgrade(self, interaction: Interaction, name: str = '', level: int = 50):
        await interaction.response.defer(thinking=True, ephemeral=True)

        if level not in range(2, 61):
            raise STWException(f'Level `{level}` is invalid, please try again.')

        account = await self.bot.get_full_account(interaction.user.id)
        heroes = [hero for hero in await account.heroes() if name.lower() in hero.name.lower()]

        if not heroes:
            raise STWException(f'Hero `{name}` not found.')

        embed_fields = self.heroes_to_fields(heroes)
        embeds = self.bot.fields_to_embeds(
            interaction,
            embed_fields,
            description=interaction.user.mention,
            author_name='Upgrade Heroes',
            author_icon=await account.icon_url()
        )

        view = Paginator(interaction, embeds)
        # noinspection PyTypeChecker
        view.add_item(UpgradeSelectionMenu(
            self.bot,
            interaction.command,
            heroes,
            level
        ))

        await interaction.followup.send(embed=embeds[0], view=view)

    @non_premium_cooldown()
    @is_logged_in()
    @is_not_blacklisted()
    @app_commands.describe(name='Name of the hero.')
    @app_commands.command(name='recycle', description='Recycle one of your heroes.')
    async def recycle(self, interaction: Interaction, name: str = ''):
        await interaction.response.defer(thinking=True, ephemeral=True)

        account = await self.bot.get_full_account(interaction.user.id)
        heroes = [hero for hero in await account.heroes() if name.lower() in hero.name.lower()]

        if not heroes:
            raise STWException(f'Hero `{name}` not found.')

        embed_fields = self.heroes_to_fields(heroes)
        embeds = self.bot.fields_to_embeds(
            interaction,
            embed_fields,
            description=interaction.user.mention,
            author_name='Recycle Heroes',
            author_icon=await account.icon_url()
        )

        view = Paginator(interaction, embeds)
        # noinspection PyTypeChecker
        view.add_item(RecycleSelectionMenu(
            self.bot,
            interaction.command,
            heroes
        ))

        await interaction.followup.send(embed=embeds[0], view=view)


async def setup(bot: STWBot):
    bot.tree.add_command(HeroCommands(bot))
