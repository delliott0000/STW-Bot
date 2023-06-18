from typing import Union

from discord import ui, SelectOption, Interaction, app_commands

from main import STWBot
from core.errors import STWException, BadRequest
from core.fortnite import Recyclable, Upgradable, Schematic


class FortniteItemSelection(SelectOption):

    def __init__(
            self,
            item_id: str
    ):
        super().__init__(label=f'Item ID: {item_id[:8]}...', value=item_id)


class RecycleSelectionMenu(ui.Select):

    def __init__(
            self,
            bot: STWBot,
            command: app_commands.Command,
            items: list[Union[Recyclable, Upgradable]]
    ):
        selectable = items[:25] if len(items) > 24 else items

        super().__init__(
            placeholder='Select Item...',
            options=[FortniteItemSelection(item.item_id) for item in selectable]
        )

        self.bot = bot
        self.command = command
        self.items = selectable

    def get_selected_item(self, interaction: Interaction):
        return [item for item in self.items if item.item_id == interaction.data['values'][0]][0]

    async def callback(self, interaction: Interaction):
        item = self.get_selected_item(interaction)

        if item.favourite is not True:
            await item.recycle()

        else:
            recycle_exception = STWException('Favorite items can not be recycled.')
            command_exception = app_commands.CommandInvokeError(self.command, recycle_exception)
            await self.bot.app_command_error(interaction, command_exception)
            return

        await self.bot.basic_response(interaction, f'Successfully recycled `{item.name}`.')


class UpgradeSelectionMenu(RecycleSelectionMenu):

    def __init__(
            self,
            bot: STWBot,
            command: app_commands.Command,
            items: list[Upgradable],
            level: int,
            material: str = ''
    ):
        super().__init__(bot, command, items)

        self.level = level
        self.material = material
        self.tier = min((level - 1) // 10 + 1, 5)

    async def callback(self, interaction: Interaction):
        item = self.get_selected_item(interaction)

        if self.level <= item.level:
            upgrade_exception = STWException(f'Invalid target level for item `{item.item_id}`.')
            command_exception = app_commands.CommandInvokeError(self.command, upgrade_exception)
            await self.bot.app_command_error(interaction, command_exception)
            return

        index = item.get_conversion_index(self.material, self.tier) if isinstance(item, Schematic) else -1

        try:
            await item.bulk_upgrade(self.level, self.tier, index=index)

        except BadRequest as error:
            command_exception = app_commands.CommandInvokeError(self.command, error)
            await self.bot.app_command_error(interaction, command_exception)
            return

        await self.bot.basic_response(interaction, f'`{item.name}` has been upgraded to level `{item.level}`!')
