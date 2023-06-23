from discord import Interaction, ui


# noinspection PyUnusedLocal
class TracebackView(ui.View):

    def __init__(
            self,
            bot,
            interaction: Interaction,
            traceback: str = '`None`'
    ):
        super().__init__(timeout=120)

        self.bot = bot
        self.interaction = interaction
        self.traceback = traceback

    @ui.button(label='Full Traceback')
    async def view_traceback(self, interaction: Interaction, button):
        await self.bot.bad_response(interaction, self.traceback)

    async def on_timeout(self):
        self.view_traceback.disabled = True
        await self.interaction.edit_original_response(view=self)
