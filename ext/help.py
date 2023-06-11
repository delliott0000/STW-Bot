from discord import app_commands, Interaction

from main import STWBot
from components.embed import CustomEmbed
from components.decorators import is_not_blacklisted, non_premium_cooldown
from components.paginator import Paginator
from resources.emojis import emojis


# noinspection PyUnresolvedReferences
class HelpCommands(app_commands.Group):

    def __init__(
            self,
            bot: STWBot,
            name: str = 'help'
    ):
        super().__init__(name=name)
        self.bot = bot

    @non_premium_cooldown()
    @is_not_blacklisted()
    @app_commands.command(name='menu', description='View information about the bot\'s commands.')
    async def menu(self, interaction: Interaction):
        await interaction.response.defer(thinking=True, ephemeral=True)

        embed_list = []
        opt_map = {True: '', False: 'opt'}

        for group in self.bot.tree.get_commands():
            if isinstance(group, app_commands.Group):

                # Syncing commands returns AppCommand objects whereas `tree.get_commands` returns Command objects
                # AppCommands have a `mention` attribute which is nice for display purposes
                # However unlike Commands, AppCommands do not have a `checks` attribute which we also need
                # So we are going to cross-reference to get both
                # (There might be a better way to do this, I don't know)
                group_from_cache = [group_ for group_ in self.bot.app_commands if group_.name == group.name][0]

                group_embed = CustomEmbed(
                    interaction,
                    title=f'{group.name.capitalize()} Commands',
                    description=f'{emojis["clock"]} **- 15s Cooldown (Non-Premium)**\n'
                                f'{emojis["premium"]} **- Premium-Only Command**'
                )
                group_embed.set_author(name='Help Menu', icon_url=self.bot.user.avatar)

                for command in group.commands:

                    premium = emojis['premium'] if [c for c in command.checks if 'is_premium' in str(c)] else ''
                    cooldown = emojis['clock'] if [c for c in command.checks if '_cooldown_' in str(c)] else ''

                    command_from_cache = [cmd for cmd in group_from_cache.options if cmd.name == command.name][0]
                    options = [f"{opt_map[opt.required]}<{opt.name}>" for opt in command_from_cache.options]

                    group_embed.add_field(
                        name=f'{premium} {cooldown} {command_from_cache.mention}',
                        value=f'> **Description:** `{command.description}`\n'
                              f'> **Parameters:** `{", ".join(options) if options else "`None`"}`',
                        inline=False
                    )

                embed_list.append(group_embed)

        for embed in embed_list:
            embed.set_footer(text=f'Page {embed_list.index(embed) + 1} of {len(embed_list)}')

        await interaction.followup.send(embed=embed_list[0], view=Paginator(interaction, embed_list))


async def setup(bot: STWBot):
    bot.tree.add_command(HelpCommands(bot))
