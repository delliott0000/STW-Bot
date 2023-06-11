from typing import Optional

from discord import (
    app_commands,
    Interaction
)


# Order of checks should typically follow a certain hierarchy
# Blacklisted -> Premium -> Logged In -> Cool Downs -> Other Checks


def is_not_blacklisted():
    async def predicate(interaction: Interaction) -> bool:
        if await interaction.client.user_is_blacklisted(interaction.user.id) is not False:
            raise app_commands.CheckFailure('You are blacklisted from using this feature.')
        return True
    return app_commands.check(predicate)


def is_premium():
    async def predicate(interaction: Interaction) -> bool:
        if await interaction.client.user_is_premium(interaction.user.id) is not True:
            raise app_commands.CheckFailure('You must be a premium user to use that command.')
        return True
    return app_commands.check(predicate)


def is_logged_in():
    def predicate(interaction: Interaction) -> bool:
        if interaction.client.user_is_logged_in(interaction.user.id) is not True:
            raise app_commands.CheckFailure('You must be logged in to use that command.')
        return True
    return app_commands.check(predicate)


def non_premium_cooldown():
    async def predicate(interaction: Interaction) -> Optional[app_commands.Cooldown]:
        if await interaction.client.user_is_premium(interaction.user.id) is not True:
            return app_commands.Cooldown(1, 15)
    return app_commands.checks.dynamic_cooldown(predicate)
