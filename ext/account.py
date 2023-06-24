from discord import app_commands, Interaction, User

from main import STWBot
from core.errors import STWException
from components.embed import CustomEmbed, EmbedField
from components.login import StaticLoginView
from components.decorators import is_not_blacklisted, is_logged_in, non_premium_cooldown
from resources.emojis import emojis


# noinspection PyUnresolvedReferences
class AccountCommands(app_commands.Group):

    def __init__(
            self,
            bot: STWBot,
            name: str = 'account'
    ):
        super().__init__(name=name)
        self.bot = bot

    @non_premium_cooldown()
    @is_not_blacklisted()
    @app_commands.command(name='login', description='Log into your Epic Games account.')
    async def login(self, interaction: Interaction):
        await interaction.response.defer(thinking=True, ephemeral=True)

        if self.bot.user_is_logged_in(interaction.user.id) is True:
            raise STWException('You are already logged in. Use `/account logout` to switch accounts.')

        instructions_embed = CustomEmbed(
            interaction,
            title='__How To Log In__',
            description=f'**• Step 1:** Log into Epic Games on your browser and open '
                        f'[this link]({self.bot.epic_api.user_auth_url}) (or click the "Get Code" button below).\n\n'
                        '**• Step 2:** Copy the 32-digit code labelled "authorizationCode".\n\n'
                        '**• Step 3:** Click the button labelled "Submit Code". '
                        'This will bring up a form where you can paste your authorization code. '
                        'Paste the code in and click "Submit".\n\n'
                        '**• Step 4:** You\'re done!\n\n'
                        '**This message will time out after 2 minutes.**\n\n'
                        f':warning: To switch accounts with **{self.bot.user.name}**, '
                        f'you must log out of your current account before logging back in on your new account.'
        )
        instructions_embed.set_author(name='Register Epic Account', icon_url=self.bot.user.avatar)
        await interaction.followup.send(embed=instructions_embed, view=StaticLoginView(self.bot, interaction))

    # Users should have the ability to log out even if they are blacklisted.
    @non_premium_cooldown()
    @is_logged_in()
    @app_commands.command(name='logout', description='Log out of your Epic Games account.')
    async def logout(self, interaction: Interaction):
        await interaction.response.defer(thinking=True, ephemeral=True)
        await self.bot.del_auth_session(interaction.user.id)
        await self.bot.basic_response(interaction, 'Successfully logged out.')

    @non_premium_cooldown()
    @is_logged_in()
    @is_not_blacklisted()
    @app_commands.command(name='info', description='View your Epic Games account information.')
    async def info(self, interaction: Interaction):
        await interaction.response.defer(thinking=True, ephemeral=True)

        account = await self.bot.get_full_account(interaction.user.id)

        info_embed = CustomEmbed(
            interaction,
            description=interaction.user.mention
        )
        info_embed.set_author(name='Epic Account Info', icon_url=await account.icon_url())
        info_embed.set_footer(text='Do not share any sensitive information with anyone!')

        info_embed.add_field(
            name='Personal Details:',
            value=f'> **Name:** `{account.name}`\n'
                  f'> **Country:** `{account.country}`\n'
                  f'> **Language:** `{account.language}`\n'
                  f'> **Date of Birth: <t:{account.birth}:D>**\n',
            inline=False
        )
        info_embed.add_field(
            name='Display Name:',
            value=f'> **Current:** `{account.display}`\n'
                  f'> **Changes:** `{account.display_changes}`\n'
                  f'> **Last Changed: <t:{account.last_display_change}:F>**\n'
                  f'> **Changeable:** '
                  f'{emojis["check" if account.can_update_display is True else "cross"]}',
            inline=False
        )
        info_embed.add_field(
            name='Email:',
            value=f'> **Current:** `{account.email}`\n'
                  f'> **Verified:** '
                  f'{emojis["check" if account.verified is True else "cross"]}',
            inline=False
        )
        info_embed.add_field(
            name='Login Details:',
            value=f'> **Last Login: <t:{account.last_login}:F>**\n'
                  f'> **Failed Login Attempts:** `{account.failed_logins}`\n'
                  f'> **TFA Enabled:** '
                  f'{emojis["check" if account.tfa_enabled else "cross"]}',
            inline=False
        )
        info_embed.add_field(
            name='Login Credentials:',
            value=f'> **Epic ID:** `{account.id}`\n'
                  f'> **Access Token:** `{account.auth_session().access_token}`\n'
                  f'> **Refresh Token:** `{account.auth_session().refresh_token}`\n'
        )

        await interaction.followup.send(embed=info_embed)

    @non_premium_cooldown()
    @is_logged_in()
    @is_not_blacklisted()
    @app_commands.describe(
        user='Search by Discord user.',
        epic_id='Search by Epic Games account ID.',
        display='Search by Epic Games display name.'
    )
    @app_commands.command(name='search', description='Search for an Epic Games account.')
    async def search(self, interaction: Interaction, user: User = None, epic_id: str = None, display: str = None):
        await interaction.response.defer(thinking=True, ephemeral=True)

        if user is not None:
            auth = self.bot.get_auth_session(user.id)
            try:
                account = await auth.get_own_partial()
            except AttributeError:
                raise STWException(f'{user.mention} is not logged in with {self.bot.user.name}.')

        else:
            auth = self.bot.get_auth_session(interaction.user.id)
            account = await auth.get_other_account(epic_id=epic_id, display=display)

        account_embed = CustomEmbed(interaction)
        account_embed.set_author(name='Epic Account Info', icon_url=await account.icon_url())

        discord_id = self.bot.discord_id_from_partial(account)
        linked = f'{emojis["check"]} <@{discord_id}>' if discord_id is not None else f'{emojis["cross"]}'

        embed_field = EmbedField(
            name='Found Account:',
            value=f'> **Display Name:** `{account.display}`\n'
                  f'> **Epic ID:** `{account.id}`\n'
                  f'> **Logged in with {self.bot.user.name}:** {linked}',
        )
        account_embed.append_field(embed_field)

        await interaction.followup.send(embed=account_embed)


async def setup(bot: STWBot):
    bot.tree.add_command(AccountCommands(bot))
