from discord import (
    Embed,
    Interaction
)


class EmbedField:

    def __init__(
            self,
            name: str = None,
            value: str = None,
            inline: bool = False
    ):
        self.name = name
        self.value = value
        self.inline = inline


class CustomEmbed(Embed):

    def __init__(
            self,
            interaction: Interaction,
            title: str = None,
            description: str = None,
            color: int = None
    ):
        super().__init__(
            title=title,
            description=description,
            color=color or interaction.client.color(interaction.guild)
        )

    def append_field(self, field: EmbedField):
        self.add_field(
            name=field.name,
            value=field.value,
            inline=field.inline
        )
