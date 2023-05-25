# TODO create trigger list command

import re

import alluka
import hikari.api.cache
import tanjun

from utils import trigger_typing
from utils.config import Config, ConfigHandler
from utils.triggers.triggers import TriggerInfo, TriggersFileHandler

trigger_handler = TriggersFileHandler()
trigger_handler.load_triggers()

################
#   Commands   #
################

component = tanjun.Component()
ct_slash_group = tanjun.slash_command_group("trigger", "Commands related to chat triggers",
                                            default_member_permissions=hikari.Permissions.MANAGE_ROLES)


@tanjun.with_str_slash_option("response5", "Other possible trigger responses", default=None, key='response5')
@tanjun.with_str_slash_option("response4", "Other possible trigger responses", default=None, key='response4')
@tanjun.with_str_slash_option("response3", "Other possible trigger responses", default=None, key='response3')
@tanjun.with_str_slash_option("response2", "Other possible trigger responses", default=None, key='response2')
@tanjun.with_member_slash_option("user4", "Additional user", default=None, key='user5')
@tanjun.with_member_slash_option("user3", "Additional user", default=None, key='user4')
@tanjun.with_member_slash_option("user2", "Additional user", default=None, key='user3')
@tanjun.with_member_slash_option("user1", "Additional user", default=None, key='user2')
@tanjun.with_bool_slash_option("overwrite", "Whether to skip checking if trigger already exists or not.", default=False)
@tanjun.with_str_slash_option("response", "Trigger response", key='response1')
@tanjun.with_member_slash_option("owner", "Owner of the trigger", key='user1')
@tanjun.with_str_slash_option("trigger", "Phrase that will trigger a response")
@ct_slash_group.as_sub_command("add", "Add a new chat trigger")
async def add(ctx: tanjun.abc.SlashContext, trigger: str, user1: hikari.Member, response1: str, overwrite: bool,
              user2: hikari.Member, user3: hikari.Member, user4: hikari.Member, user5: hikari.Member,
              response2: str, response3: str, response4: str, response5: str,
              config: Config = alluka.inject(type=Config)):
    await trigger_typing(ctx)

    args = locals()
    for key in list(args.keys()):
        if re.match("user\d|response\d", key) is not None:
            continue

        del args[key]

    trigger_info: TriggerInfo = {
        "owner": [user.id for user in args.values() if isinstance(user, hikari.Member)],
        "reply": [response for response in args.values() if isinstance(response, str)],
        "enabled": True
    }

    try:
        await trigger_handler.add_trigger(trigger, trigger_info, overwrite)

    except KeyError:
        embed = hikari.Embed(
            title='Error',
            description=f'Trigger `{trigger}` already exists. Set overwrite to True if you want to replace.',
            color=config['colors']['error']
        )
        await ctx.respond(embed=embed)

    else:
        embed = hikari.Embed(
            title='Success',
            description='Chat trigger added successfully',
            color=config['colors']['success']
        )
        await ctx.respond(embed=embed)


@tanjun.with_str_slash_option("trigger", "The trigger to remove")
@ct_slash_group.as_sub_command("remove", "Remove a chat trigger")
async def remove(ctx: tanjun.abc.Context,
                 trigger: str,
                 config: Config = alluka.inject(type=Config)
                 ):
    removed = await trigger_handler.remove_trigger(trigger)
    if removed:
        embed = hikari.Embed(
            title='Success',
            description=f'Removed trigger `{trigger}`.',
            color=config['colors']['success']
        )
    else:
        embed = hikari.Embed(
            title='Error',
            description=f'Trigger `{trigger}` not found.',
            color=config['colors']['success']
        )

    await ctx.respond(embed=embed)

@remove.with_str_autocomplete("trigger")
async def trigger_autocomplete(ctx: tanjun.abc.AutocompleteContext, value: str) -> None:
    triggers = trigger_handler.get_triggers()
    
    choices = {}

    i = 0

    for t in triggers:
        if value not in t:
            continue
        choices[t] = t
        
        i += 1

        if i == 25:
            break
    
    await ctx.set_choices(choices)


component.load_from_scope()


@tanjun.as_loader()
def load(client: tanjun.Client) -> None:
    if not ConfigHandler().get_config()['modules']['triggers']:
        return

    client.add_component(component)


@tanjun.as_unloader()
def unload(client) -> None:
    client.remove_component(component)
