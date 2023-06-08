from discord import app_commands, Interaction

from main import STWBot
from core.accounts import FriendEpicAccount
from components.embed import EmbedField
from components.decorators import is_not_blacklisted, is_logged_in
from components.paginator import Paginator
from resources.emojis import emojis


# noinspection PyUnresolvedReferences
class FriendCommands(app_commands.Group):

    def __init__(
            self,
            bot: STWBot,
            name: str = 'friends'
    ):
        super().__init__(name=name)
        self.bot = bot

    async def friends_to_fields(self, interaction: Interaction, friend_type: str = 'friends') -> dict:
        await interaction.response.defer(thinking=True, ephemeral=True)

        account = await self.bot.get_full_account(interaction.user.id)
        friends = await account.friends_list(friend_type)
        icon_url = await account.icon_url()

        field_list = []

        for friend in friends:

            mutual = f'> **Mutual Friends:** `{friend.mutual}`\n' if isinstance(friend, FriendEpicAccount) else ""

            discord_id = self.bot.discord_id_from_partial(friend)
            linked = f'{emojis["check"]} <@{discord_id}>' if discord_id is not None else f'{emojis["cross"]}'

            field = EmbedField(
                name=friend.display,
                value=f'> **Epic ID:** `{friend.id}`\n'
                      f'{mutual}'
                      f'> **Logged in with {self.bot.user.name}:** {linked}',
            )

            field_list.append(field)

        return {'fields': field_list, 'icon_url': icon_url}

    @app_commands.checks.cooldown(1, 15)
    @is_logged_in()
    @is_not_blacklisted()
    @app_commands.command(name='list', description='View your friends list.')
    async def list(self, interaction: Interaction):
        embed_data = await self.friends_to_fields(interaction)
        embed_list = self.bot.fields_to_embeds(
            interaction,
            embed_data['fields'],
            description=interaction.user.mention,
            author_name='Friends List',
            author_icon=embed_data['icon_url']
        )
        await interaction.followup.send(embed=embed_list[0], view=Paginator(interaction, embed_list))

    @app_commands.checks.cooldown(1, 15)
    @is_logged_in()
    @is_not_blacklisted()
    @app_commands.command(name='incoming', description='View your incoming friend requests.')
    async def incoming(self, interaction: Interaction):
        embed_data = await self.friends_to_fields(interaction, friend_type='incoming')
        embed_list = self.bot.fields_to_embeds(
            interaction,
            embed_data['fields'],
            description=interaction.user.mention,
            author_name='Incoming Requests',
            author_icon=embed_data['icon_url']
        )
        await interaction.followup.send(embed=embed_list[0], view=Paginator(interaction, embed_list))

    @app_commands.checks.cooldown(1, 15)
    @is_logged_in()
    @is_not_blacklisted()
    @app_commands.command(name='outgoing', description='View your outgoing friend requests.')
    async def outgoing(self, interaction: Interaction):
        embed_data = await self.friends_to_fields(interaction, friend_type='outgoing')
        embed_list = self.bot.fields_to_embeds(
            interaction,
            embed_data['fields'],
            description=interaction.user.mention,
            author_name='Outgoing Requests',
            author_icon=embed_data['icon_url']
        )
        await interaction.followup.send(embed=embed_list[0], view=Paginator(interaction, embed_list))

    @app_commands.checks.cooldown(1, 15)
    @is_logged_in()
    @is_not_blacklisted()
    @app_commands.command(name='suggested', description='View your suggested friends list.')
    async def suggested(self, interaction: Interaction):
        embed_data = await self.friends_to_fields(interaction, friend_type='suggested')
        embed_list = self.bot.fields_to_embeds(
            interaction,
            embed_data['fields'],
            description=interaction.user.mention,
            author_name='Suggested Friends',
            author_icon=embed_data['icon_url']
        )
        await interaction.followup.send(embed=embed_list[0], view=Paginator(interaction, embed_list))

    @app_commands.checks.cooldown(1, 15)
    @is_logged_in()
    @is_not_blacklisted()
    @app_commands.command(name='blocklist', description='View your list of blocked users.')
    async def blocklist(self, interaction: Interaction):
        embed_data = await self.friends_to_fields(interaction, friend_type='blocklist')
        embed_list = self.bot.fields_to_embeds(
            interaction,
            embed_data['fields'],
            description=interaction.user.mention,
            author_name='Blocked Users',
            author_icon=embed_data['icon_url']
        )
        await interaction.followup.send(embed=embed_list[0], view=Paginator(interaction, embed_list))

    @app_commands.checks.cooldown(1, 15)
    @is_logged_in()
    @is_not_blacklisted()
    @app_commands.describe(display='Epic account display name.')
    @app_commands.command(name='add', description='Send a friend request to another user.')
    async def add(self, interaction: Interaction, display: str):
        await interaction.response.defer(thinking=True, ephemeral=True)

        auth_session = self.bot.get_auth_session(interaction.user.id)
        friend_account = await auth_session.get_other_account(display=display)

        epic_account = await auth_session.get_own_account()
        await epic_account.add_friend(friend_account.id)

        await self.bot.basic_response(interaction, f'Successfully friended `{friend_account.display}`.')

    @app_commands.checks.cooldown(1, 15)
    @is_logged_in()
    @is_not_blacklisted()
    @app_commands.describe(display='Epic account display name.')
    @app_commands.command(name='remove', description='Remove a user from your friends list.')
    async def remove(self, interaction: Interaction, display: str):
        await interaction.response.defer(thinking=True, ephemeral=True)

        auth_session = self.bot.get_auth_session(interaction.user.id)
        friend_account = await auth_session.get_other_account(display=display)

        epic_account = await auth_session.get_own_account()
        await epic_account.del_friend(friend_account.id)

        await self.bot.basic_response(interaction, f'Successfully unfriended `{friend_account.display}`.')

    @app_commands.checks.cooldown(1, 15)
    @is_logged_in()
    @is_not_blacklisted()
    @app_commands.describe(display='Epic account display name.')
    @app_commands.command(name='block', description='Block another Epic Games user.')
    async def block(self, interaction: Interaction, display: str):
        await interaction.response.defer(thinking=True, ephemeral=True)

        auth_session = self.bot.get_auth_session(interaction.user.id)
        friend_account = await auth_session.get_other_account(display=display)

        epic_account = await auth_session.get_own_account()
        await epic_account.block(friend_account.id)

        await self.bot.basic_response(interaction, f'Successfully blocked `{friend_account.display}`.')

    @app_commands.checks.cooldown(1, 15)
    @is_logged_in()
    @is_not_blacklisted()
    @app_commands.describe(display='Epic account display name.')
    @app_commands.command(name='unblock', description='Unblock another Epic Games user.')
    async def unblock(self, interaction: Interaction, display: str):
        await interaction.response.defer(thinking=True, ephemeral=True)

        auth_session = self.bot.get_auth_session(interaction.user.id)
        friend_account = await auth_session.get_other_account(display=display)

        epic_account = await auth_session.get_own_account()
        await epic_account.unblock(friend_account.id)

        await self.bot.basic_response(interaction, f'Successfully unblocked `{friend_account.display}`.')


async def setup(bot: STWBot):
    bot.tree.add_command(FriendCommands(bot))
