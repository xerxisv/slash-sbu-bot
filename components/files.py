# TODO implement autofill for file name
import os
from pathlib import Path
from typing import Annotated

import hikari
import tanjun

from utils.config import ConfigHandler

################
#   Commands   #
################

command_component = tanjun.Component()

command_group = tanjun.SlashCommandGroup("file", "Commands regarding files in the bot's data folder",
                                         default_member_permissions=hikari.Permissions.MANAGE_CHANNELS)

command_component.with_slash_command(command_group)


@tanjun.annotations.with_annotated_args(follow_wrapped=True)
@command_group.as_sub_command("fetch", "Fetches a file with the given name", default_to_ephemeral=True)
async def file_fetch(ctx: tanjun.abc.SlashContext,
                     file_name: Annotated[tanjun.annotations.Str, "File name with extension"]):
    if file_name.find('/') != -1:
        await ctx.respond('Forbidden.')
        return

    file = Path(os.getcwd() + f'/data/{file_name}')

    if not file.is_file():
        await ctx.respond('File not found')
        return

    file = hikari.File(file)
    await ctx.respond(attachment=file)


@tanjun.as_loader()
def load(client: tanjun.Client):
    if not ConfigHandler().get_config()['modules']['files']:
        return

    client.add_component(command_component)


@tanjun.as_unloader()
def unload(client: tanjun.Client):
    client.remove_component_by_name(command_component.name)
