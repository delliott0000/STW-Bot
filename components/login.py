from discord import (
    ui,
    ButtonStyle,
    Button,
    Interaction
)

from main import STWBot
from core.errors import BadRequest


class StaticLoginView(ui.View):

    def __init__(
            self,
            bot: STWBot,
            interaction: Interaction
    ):
        super().__init__(timeout=120)

        self.add_item(ui.Button(label='Get Code', style=ButtonStyle.grey, url=bot.epic_api.user_auth_url))

        self.bot = bot
        self.interaction = interaction

    # noinspection PyUnusedLocal
    @ui.button(label='Submit Code', style=ButtonStyle.grey)
    async def submit(
            self,
            interaction: Interaction,
            button: Button
    ):
        # noinspection PyUnresolvedReferences
        await interaction.response.send_modal(LoginModal(self.bot))

    async def on_timeout(self):
        self.submit.disabled = True
        await self.interaction.edit_original_response(view=self)


class LoginModal(ui.Modal):

    def __init__(
            self,
            bot: STWBot
    ):
        super().__init__(title='Authorize Account Access', timeout=None)

        self.bot = bot

    code_field = ui.TextInput(label='Enter Auth Code', placeholder='Authorization Code', required=True)

    async def on_submit(self, interaction: Interaction):
        try:
            auth_session = await self.bot.epic_api.create_auth_session(self.code_field.value, interaction.user.id)
        except BadRequest:
            await self.bot.bad_response(interaction, 'The code you entered is invalid, please try again.')
            return

        self.bot.add_auth_session(auth_session)

        display_name = (await auth_session.get_own_account()).display
        await self.bot.basic_response(interaction, f'Successfully logged in as `{display_name}`.')
