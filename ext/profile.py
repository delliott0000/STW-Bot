from discord import app_commands, Interaction

from main import STWBot
from core.fortnite import AccountResource
from components.decorators import is_not_blacklisted, is_logged_in
from components.embed import CustomEmbed
from resources.emojis import emojis


# noinspection PyUnresolvedReferences
class ProfileCommands(app_commands.Group):

    def __init__(
            self,
            bot: STWBot,
            name: str = 'profile'
    ):
        super().__init__(name=name)
        self.bot = bot

        # Categorising account resources, so we can easily group/display them later on
        self._RESOURCE_MAPPING = {
            'Perk-Up': ['AMP-UP!', 'FIRE-UP!', 'FROST-UP!', 'Uncommon PERK-UP!', 'Rare PERK-UP!', 'Epic PERK-UP!',
                        'Legendary PERK-UP!'],
            'Re-Perk': ['RE-PERK!', 'Core RE-PERK!'],
            'Evo Materials': ['Pure Drop of Rain', 'Lightning in a Bottle', 'Eye of the Storm', 'Storm Shard'],
            'Manuals': ['Trap Designs', 'Training Manual', 'Weapon Designs'],
            'Superchargers': ['Trap Supercharger', 'Weapon Supercharger', 'Hero Supercharger', 'Survivor Supercharger'],
            'XP': ['Hero XP', 'Survivor XP', 'Schematic XP', 'Venture XP'],
            'Flux': ['Legendary Flux', 'Epic Flux', 'Rare Flux'],
            'Vouchers': ['Weapon Research Voucher', 'Hero Recruitment Voucher'],
            'Currency': ['Gold', 'X-Ray Tickets']
        }

    @staticmethod
    def resource_group_to_string(resources: list[AccountResource], name_list: list[str]):
        return '\n'.join([f'> {resource.emoji} **{resource.quantity:,}**'
                          for resource in resources if resource.name in name_list]) or '> `None`'

    @app_commands.checks.cooldown(1, 15)
    @is_logged_in()
    @is_not_blacklisted()
    @app_commands.command(name='resources', description='View your own or another player\'s account resources.')
    async def resources(self, interaction: Interaction, display: str = None):
        await interaction.response.defer(thinking=True, ephemeral=True)

        auth = self.bot.get_auth_session(interaction.user.id)
        account = await auth.get_other_account(display=display) if display is not None else await auth.get_own_account()
        icon_url = await account.icon_url()
        resources = await account.resources()

        embed = CustomEmbed(
            interaction,
            description=f'**IGN:** `{account.display}`'
        )
        embed.set_author(name='Profile Resources', icon_url=icon_url)
        embed.set_footer(text='*Weapon/Hero Voucher counts may be incorrect due to an API issue.')

        for item in self._RESOURCE_MAPPING:
            embed.add_field(
                name=item,
                value=self.resource_group_to_string(resources, self._RESOURCE_MAPPING[item])
            )
        embed.insert_field_at(2, name='\u200b', value='\u200b')

        try:
            # Should deal with seasonal tickets changing every few months
            tickets = [r for r in resources if 'Ticket' in r.name and 'X-Ray' not in r.name][0]
            prev_field = embed.fields[-1]
            embed.set_field_at(
                -1,
                name=prev_field.name,
                value=prev_field.value + f'\n> {emojis["resources"]["Tickets"]} **{tickets.quantity:,}**'
            )
        except KeyError:
            pass

        await interaction.followup.send(embed=embed)


async def setup(bot: STWBot):
    bot.tree.add_command(ProfileCommands(bot))
