# TODO create trigger list command
import json
import re
from math import ceil

import alluka
import hikari.api.cache
import tanjun
from miru.ext import nav

from utils import trigger_typing
from utils.config import Config, ConfigHandler
from utils.error_utils import log_error
from utils.user_triggers.user_triggers import TriggerInfo, UserTriggersFileHandler

trigger_handler = UserTriggersFileHandler()
trigger_handler.load_triggers()

################
#   Commands   #
################

component = tanjun.Component()
ct_slash_group = tanjun.slash_command_group("trigger", "Commands related to chat triggers",
                                            default_member_permissions=hikari.Permissions.MANAGE_ROLES)
ct_json_slash_group = ct_slash_group.make_sub_group("json", "Edit triggers file directly", default_to_ephemeral=True)


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
async def ct_add(ctx: tanjun.abc.SlashContext, trigger: str, user1: hikari.Member, response1: str, overwrite: bool,
                 user2: hikari.Member, user3: hikari.Member, user4: hikari.Member, user5: hikari.Member,
                 response2: str, response3: str, response4: str, response5: str,
                 config: Config = alluka.inject(type=Config)):
    await trigger_typing(ctx)

    args = locals()
    for key in list(args.keys()):
        if re.match("user[1-5]|response[1-5]", key) is not None:
            continue

        del args[key]

    trigger_info: TriggerInfo = {
        "owner": [user.id for user in args.values() if isinstance(user, hikari.Member)],
        "reply": [response for response in args.values() if isinstance(response, str)],
        "enabled": True
    }

    if not await trigger_handler.add_trigger(trigger, trigger_info, overwrite):
        embed = hikari.Embed(
            title='Error',
            description=f'Trigger `{trigger}` already exists. Set overwrite to True if you want to replace.',
            color=config['colors']['error']
        )
        await ctx.respond(embed=embed)

        return


    embed = hikari.Embed(
        title='Success',
        description='Chat trigger added successfully',
        color=config['colors']['success']
    )
    await ctx.respond(embed=embed)


@tanjun.with_str_slash_option("trigger", "The trigger to remove")
@ct_slash_group.as_sub_command("remove", "Remove a chat trigger")
async def ct_remove(ctx: tanjun.abc.SlashContext, trigger: str, config: Config = alluka.inject(type=Config)):
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
            color=config['colors']['error']
        )

    await ctx.respond(embed=embed)


@tanjun.with_str_slash_option("trigger", "The trigger to toggle")
@ct_slash_group.as_sub_command("toggle", "Enable/disable a trigger")
async def ct_toggle(ctx: tanjun.abc.SlashContext, trigger: str, config: Config = alluka.inject(type=Config)):
    embed = None
    try:
        state = await trigger_handler.toggle_trigger(trigger)
    except KeyError:
        embed = hikari.Embed(
            title='Error',
            description=f'Trigger `{trigger}` not found.',
            color=config['colors']['error']
        )
    else:
        embed = hikari.Embed(
            title='Success',
            description=f'Trigger `{trigger}` is now {"enabled" if state else "disabled"}.',
            color=config['colors']['success']
        )
    finally:
        await ctx.respond(embed=embed)


@ct_slash_group.as_sub_command("list", "List all the triggers")
async def ct_list(ctx: tanjun.abc.SlashContext, config: Config = alluka.inject(type=Config)):
    triggers = trigger_handler.triggers()

    if (triggers_num := len(triggers)) == 0:
        embed = hikari.Embed(
            title='Nothing to show',
            description='No triggers found',
            color=config['colors']['secondary']
        )
        await ctx.respond(embed=embed)
        return

    pages = []
    pages_num = ceil(triggers_num / 10)
    for page in range(1, pages_num + 1):
        embed = hikari.Embed(
            title='Triggers',
            color=config['colors']['primary']
        )
        for t_key in list(triggers.keys())[(page - 1) * 10: page * 10]:
            trigger = triggers[t_key]
            users_str = ""
            if len(users := trigger['owner'][1:]):
                users_str = "*Users*: "
                users_str += " ".join([f'<@{user}>' for user in users])  # Python is a divine gift to humanity
                users_str += '\n'
            if isinstance(replies := trigger['reply'], list):
                replies_str = "*Replies*: \n" + "\n".join([f'- `{reply}`' for reply in replies])
            else:
                replies_str = "*Reply*: " + f"`{replies}`" if '\n' not in replies else f"```{replies}```"

            embed.add_field(
                name=f"__{t_key}__",
                value=f"*Owner*: <@{trigger['owner'][0]}>\n"
                      f"{users_str}"
                      f"{replies_str}\n"
                      f"*Enabled*: {bool(trigger['enabled'])}"
            )
        pages.append(embed)

    navigator = nav.NavigatorView(pages=pages, autodefer=True)
    await navigator.send(ctx.interaction)


###################
#  JSON Commands  #
###################

@tanjun.with_str_slash_option("trigger", "The trigger")
@ct_json_slash_group.as_sub_command("get", "Get the json for the given trigger")
async def json_get(ctx: tanjun.abc.SlashContext, trigger: str, config: Config = alluka.inject(type=Config)):
    trigger = trigger.upper()
    if trigger not in trigger_handler.triggers():
        embed = hikari.Embed(
            title='Error',
            description=f'Trigger `{trigger}` not found.',
            color=config['colors']['error']
        )
        await ctx.respond(embed=embed)
        return

    json_str = json.dumps(trigger_handler.triggers()[trigger], indent=4)
    attachment = hikari.Bytes(bytes(json_str, encoding='utf-8'), f'{trigger}.json')
    await ctx.respond(attachment=attachment)


@tanjun.with_attachment_slash_option("json", "The json to overwrite the trigger", key="attachment")
@tanjun.with_str_slash_option("trigger", "The trigger to overwrite")
@ct_json_slash_group.as_sub_command("set", "Overwrites a trigger with the given json data")
async def json_set(ctx: tanjun.abc.SlashContext, trigger: str, attachment: hikari.Attachment,
                   config: Config = alluka.inject(type=Config)):
    trigger = trigger.upper()
    embed = None
    try:
        fs = await attachment.read()
        dct = json.loads(fs)

        trigger_handler.triggers()[trigger] = dct
        trigger_handler.reload_triggers()
    except Exception as exception:
        await log_error(ctx, exception)
        embed = hikari.Embed(
            title='Error',
            description=f"Something went wrong. See <#{config['bot_log_channel_id']}>",
            color=config['colors']['error']
        )
    else:
        embed = hikari.Embed(
            title='Success',
            description=f'Trigger `{trigger}` successfully set',
            color=config['colors']['success']
        )
    finally:
        await ctx.respond(embed=embed)


@json_set.with_str_autocomplete("trigger")
@json_get.with_str_autocomplete("trigger")
@ct_remove.with_str_autocomplete("trigger")
@ct_toggle.with_str_autocomplete("trigger")
async def trigger_autocomplete(ctx: tanjun.abc.AutocompleteContext, value: str) -> None:
    triggers = trigger_handler.triggers()

    choices = {}

    for i, t in enumerate(triggers):
        if not t.startswith(value.upper()):
            continue
        choices[t] = t

        if i == 24:
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
