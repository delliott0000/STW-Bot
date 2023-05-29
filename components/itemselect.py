from typing import Union

from discord import ui, SelectOption, Interaction

from main import STWBot
from core.errors import BadRequest
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
            items: list[Union[Recyclable, Upgradable]]
    ):
        selectable = items[:25] if len(items) > 24 else items

        super().__init__(
            placeholder='Select Item...',
            options=[FortniteItemSelection(item.item_id) for item in selectable]
        )

        self.bot = bot
        self.items = selectable

    def get_selected_item(self, interaction: Interaction):
        return [item for item in self.items if item.item_id == interaction.data['values'][0]][0]

    async def callback(self, interaction: Interaction):
        item = self.get_selected_item(interaction)

        if item.favourite is True:
            await self.bot.bad_response(interaction, 'Favorite items can not be recycled.')
            return
        await item.recycle()

        await self.bot.basic_response(
            interaction,
            f'Successfully recycled `{item.name}`.'
        )


class UpgradeSelectionMenu(RecycleSelectionMenu):

    def __init__(
            self,
            bot: STWBot,
            items: list[Upgradable],
            increment: int = 10
    ):
        super().__init__(bot, items)

        self.increment = increment

    async def callback(self, interaction: Interaction):
        item = self.get_selected_item(interaction)

        count = 0
        for i in range(self.increment):
            try:
                await item.upgrade()
                count += 1
            except BadRequest as error:
                if count == 0:
                    await self.bot.bad_response(interaction, str(error))
                    return
                break

        await self.bot.basic_response(
            interaction,
            f'Successfully upgraded `{item.name}` to level `{item.level}`.'
        )


class EvolveSelectionMenu(RecycleSelectionMenu):

    def __init__(
            self,
            bot: STWBot,
            items: list[Upgradable],
            material: str = ''
    ):
        super().__init__(bot, items)

        self.material = material

    async def callback(self, interaction: Interaction):
        item = self.get_selected_item(interaction)

        index = item.get_conversion_index(target_material=self.material) if isinstance(item, Schematic) else 0
        try:
            await item.evolve(index=index)
        except BadRequest as error:
            await self.bot.bad_response(interaction, str(error))
            return

        await self.bot.basic_response(
            interaction,
            f'Successfully evolved `{item.name}` to tier `{item.tier}`.'
        )
