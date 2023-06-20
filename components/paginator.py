from discord import ui, ButtonStyle


# noinspection PyUnusedLocal
class Paginator(ui.View):

    def __init__(
            self,
            interaction,
            embeds
    ):
        super().__init__(timeout=120)

        self.interaction = interaction
        self.embeds = embeds
        self.current_page = 1

        self.update_buttons()

    def update_buttons(self):
        for button in self.children:
            button.disabled = False
        self.firs_page.disabled = self.prev_page.disabled = self.current_page == 1
        self.next_page.disabled = self.last_page.disabled = self.current_page == len(self.embeds)

    async def edit_page(self, interaction):
        await interaction.response.defer()
        self.update_buttons()
        await self.interaction.edit_original_response(embed=self.embeds[self.current_page - 1], view=self)

    @ui.button(label='<<')
    async def firs_page(self, interaction, button):
        self.current_page = 1
        await self.edit_page(interaction)

    @ui.button(label='<', style=ButtonStyle.blurple)
    async def prev_page(self, interaction, button):
        self.current_page -= 1
        await self.edit_page(interaction)

    @ui.button(label='>', style=ButtonStyle.blurple)
    async def next_page(self, interaction, button):
        self.current_page += 1
        await self.edit_page(interaction)

    @ui.button(label='>>')
    async def last_page(self, interaction, button):
        self.current_page = len(self.embeds)
        await self.edit_page(interaction)

    async def on_timeout(self):
        for button in self.children:
            button.disabled = True
        await self.interaction.edit_original_response(view=self)
