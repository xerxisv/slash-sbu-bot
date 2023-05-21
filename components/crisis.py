# Welcome to my version of hell
from typing import Annotated

import aiosqlite
import hikari
import tanjun

from utils import trigger_typing
from utils.checks.role_checks import admin_check, jr_admin_check
from utils.config import ConfigHandler
from utils.database import DBConnection

################
#    Config    #
################

db: aiosqlite.Connection = DBConnection().get_db()
config = ConfigHandler().get_config()

CHANNEL_CHANGES: dict[int, list[int]] = {}
TICKET_CHANNEL_CHANGES: dict[int, list[int]] = {}

errors: list[tuple[str, str]] = []
locked_channels = []

is_crisis_active = False
is_crisis_loading = False


#############################
#    Commands' Functions    #
#############################

async def secure_everyone_role(everyone_role: hikari.Role):
    everyone_perms = everyone_role.permissions & ~(
            hikari.Permissions.SEND_MESSAGES | hikari.Permissions.SEND_MESSAGES_IN_THREADS | hikari.Permissions.CONNECT)

    await everyone_role.app.rest.edit_role(permissions=everyone_perms, role=everyone_role.id, guild=config['server_id'])


async def restore_everyone_role(everyone_role: hikari.Role):
    try:
        everyone_perms = everyone_role.permissions | hikari.Permissions.SEND_MESSAGES \
                         | hikari.Permissions.SEND_MESSAGES_IN_THREADS | hikari.Permissions.CONNECT

        await everyone_role.app.rest.edit_role(guild=config['server_id'], role=everyone_role.id,
                                               permissions=everyone_perms)
    except hikari.HikariError as _ignored:
        errors.append(('.', '`@everyone`'))


async def secure_ticket_channels(ctx: tanjun.abc.Context, everyone_role: hikari.Role):
    for channel_id in config['crisis']['ticket_channels']:
        try:
            channel: hikari.PermissibleGuildChannel = ctx.get_guild().get_channel(channel_id)
            overwrites = channel.permission_overwrites
        except AttributeError as exception:
            errors.append((exception.name, str(channel_id)))
            continue

        TICKET_CHANNEL_CHANGES[channel_id] = []

        everyone_overwrites = overwrites.get(everyone_role.id)
        if not (everyone_overwrites.deny & hikari.Permissions.VIEW_CHANNEL):
            everyone_overwrites.allow = everyone_overwrites.allow & ~hikari.Permissions.VIEW_CHANNEL
            everyone_overwrites.deny = everyone_overwrites.deny | hikari.Permissions.VIEW_CHANNEL

            TICKET_CHANNEL_CHANGES[channel_id].append(config['crisis']['everyone_role_id'])

        for role in overwrites.keys():
            if role in config['crisis']['ignored_roles']:
                continue

            role_overwrites = overwrites.get(role)
            if not (role_overwrites.deny & hikari.Permissions.VIEW_CHANNEL):
                role_overwrites.allow = role_overwrites.allow & ~hikari.Permissions.VIEW_CHANNEL
                role_overwrites.deny = role_overwrites.deny | hikari.Permissions.VIEW_CHANNEL

                TICKET_CHANNEL_CHANGES[channel_id].append(role)

        locked_channels.append(channel_id)

        try:
            await channel.edit(name=channel.name + '-☆', permission_overwrites=overwrites.values())
        except (hikari.BadRequestError, hikari.InternalServerError):
            errors.append(('Could not change name', str(channel_id)))


async def restore_ticket_channels(ctx: tanjun.abc.Context):
    for channel_id in TICKET_CHANNEL_CHANGES:
        try:
            channel: hikari.PermissibleGuildChannel = ctx.get_guild().get_channel(channel_id)
            overwrites = channel.permission_overwrites
        except AttributeError as exception:
            errors.append((exception.name, str(channel_id)))
            continue

        for role_id in TICKET_CHANNEL_CHANGES[channel_id]:
            role_overwrites = overwrites.get(hikari.Snowflake(role_id))
            role_overwrites.allow = role_overwrites.allow | hikari.Permissions.VIEW_CHANNEL
            role_overwrites.deny = role_overwrites.deny & ~hikari.Permissions.VIEW_CHANNEL

        await channel.edit(name=channel.name.replace('-☆', ''), permission_overwrites=overwrites.values())


async def secure_text_channels(ctx: tanjun.abc.Context):
    for channel_id in ctx.get_guild().get_channels():
        channel = ctx.get_guild().get_channel(channel_id)

        if not channel.parent_id or channel.parent_id in config['crisis']['ignored_categories'] or \
                channel_id in config['crisis']['ignored_roles']:
            continue

        # flags if the overwrites have been changed
        overwrites_changed = False
        if isinstance(channel, (hikari.GuildTextChannel, hikari.GuildForumChannel)):

            overwrites = channel.permission_overwrites
            CHANNEL_CHANGES[channel_id] = []

            for role_id in overwrites.keys():
                if role_id in config['crisis']['ignored_roles']:
                    continue

                role_overwrites = overwrites.get(role_id)

                if role_overwrites.allow & hikari.Permissions.SEND_MESSAGES:
                    overwrites_changed = True

                    CHANNEL_CHANGES[channel_id].append(role_id)

                    # remove post perms from allowed perms
                    overwrites.get(role_id).allow = role_overwrites.allow & ~(
                            hikari.Permissions.SEND_MESSAGES | hikari.Permissions.SEND_MESSAGES_IN_THREADS)
                    # add them to denied perms
                    overwrites.get(role_id).deny = role_overwrites.deny \
                                                   | hikari.Permissions.SEND_MESSAGES \
                                                   | hikari.Permissions.SEND_MESSAGES_IN_THREADS

            if not overwrites_changed:
                del CHANNEL_CHANGES[channel_id]
                continue

            try:
                await channel.edit(permission_overwrites=overwrites.values(), name=channel.name + '-☆')
            except (hikari.BadRequestError, hikari.InternalServerError) as exception:
                errors.append((exception.name, str(channel_id)))
            else:
                locked_channels.append(channel_id)


async def restore_text_channels(ctx: tanjun.abc.Context):
    for channel_id in CHANNEL_CHANGES:
        channel = ctx.get_guild().get_channel(channel_id)
        overwrites = channel.permission_overwrites

        for _id in CHANNEL_CHANGES[channel_id]:
            obj: hikari.Role | hikari.User
            obj = ctx.get_guild().get_role(_id)
            if obj is None:
                obj = await ctx.rest.fetch_user(_id)

            if obj is None:
                errors.append((str(_id), str(channel_id)))
                continue

            role_overwrites = overwrites.get(hikari.Snowflake(_id))

            overwrites.get(obj.id).allow = role_overwrites.allow \
                                           | hikari.Permissions.SEND_MESSAGES \
                                           | hikari.Permissions.SEND_MESSAGES_IN_THREADS
            overwrites.get(obj.id).deny = role_overwrites.deny & ~(
                    hikari.Permissions.SEND_MESSAGES | hikari.Permissions.SEND_MESSAGES_IN_THREADS)

        try:
            await channel.edit(permission_overwrites=overwrites.values(), name=channel.name.replace('-☆', ''))
        except (hikari.BadRequestError, hikari.InternalServerError) as exception:
            errors.append((exception.name, str(channel_id)))


################
#   Commands   #
################

component = tanjun.Component()

crisis_slash_group = tanjun.slash_command_group("crisis", "Channel lockdown commands",
                                                default_member_permissions=hikari.Permissions.MANAGE_ROLES)
crisis_list_slash_group = crisis_slash_group.make_sub_group("list", "Debug info regarding an ongoing crisis")

component.add_check(jr_admin_check)
component.with_command(crisis_slash_group)


@component.with_command
@tanjun.as_message_command_group("crisis")
async def crisis_msg_group(_):
    pass


@component.with_command
@crisis_msg_group.as_sub_command("help")
async def crisis_help(ctx: tanjun.abc.MessageContext):
    await trigger_typing(ctx)
    help_embed = hikari.Embed(
        title='Command Help',
        color=config['colors']['primary']
    )

    help_embed.add_field(name='Start crisis', value='`+crisis initialize`', inline=False)
    help_embed.add_field(name='Stop crisis', value='`+crisis restore`', inline=False)
    help_embed.add_field(name='Add channel to crisis', value='`+crisis add <channel>`', inline=False)
    help_embed.add_field(name='List affected channels', value='`+crisis list channels`', inline=False)
    help_embed.add_field(name='List errors', value='`+crisis list errors`', inline=False)

    await ctx.respond(embed=help_embed)


@tanjun.with_cooldown("crisis", follow_wrapped=True, owners_exempt=False)
@crisis_msg_group.as_sub_command("initialize")
@crisis_slash_group.as_sub_command("initialize", "Initializes a crisis")
async def crisis_initialize(ctx: tanjun.abc.Context):
    await trigger_typing(ctx)

    global is_crisis_active
    global is_crisis_loading

    if is_crisis_active:
        embed = hikari.Embed(
            title='',
            description='A crisis is already active.',
            color=config['colors']['secondary']
        )
        await ctx.respond(embed=embed)
        return

    embed = hikari.Embed(
        title='',
        description='Crisis Initializing <a:loading:978732444998070304>',
        color=config['colors']['secondary']
    )
    await ctx.respond(embed=embed)

    # clear possible leftovers
    errors.clear()

    is_crisis_active = True
    is_crisis_loading = True

    everyone_role = ctx.get_guild().get_role(config['crisis']['everyone_role_id'])

    await secure_everyone_role(everyone_role)
    await secure_ticket_channels(ctx, everyone_role)
    await secure_text_channels(ctx)

    embed = hikari.Embed(
        title='',
        description='Crisis Initialized',
        color=config['colors']['success']
    )
    await ctx.edit_initial_response(embed=embed)
    is_crisis_loading = False


@tanjun.with_check(admin_check, follow_wrapped=True)
@crisis_msg_group.as_sub_command("restore")
@crisis_slash_group.as_sub_command("restore", "Restores the changes from an ongoing crisis")
async def crisis_restore(ctx: tanjun.abc.Context):
    await trigger_typing(ctx)

    global is_crisis_active
    global is_crisis_loading

    if not is_crisis_active:
        embed = hikari.Embed(
            title='Error',
            description='No ongoing crisis',
            color=config['colors']['error']
        )
        await ctx.edit_initial_response(embed=embed)
        return

    if is_crisis_loading:
        embed = hikari.Embed(
            title='Error',
            description='A crisis is initializing. Please wait',
            color=config['colors']['error']
        )
        await ctx.edit_initial_response(embed=embed)
        return

    embed = hikari.Embed(
        title='',
        description='Restoring Crisis Changes <a:loading:978732444998070304>',
        color=config['colors']['secondary']
    )

    await ctx.respond(embed=embed)

    errors.clear()  # clear possible leftover errors

    everyone_role = ctx.get_guild().get_role(config['crisis']['everyone_role_id'])

    await restore_everyone_role(everyone_role)
    await restore_ticket_channels(ctx)
    await restore_text_channels(ctx)

    embed = hikari.Embed(
        title='',
        description='Crisis Restored',
        color=config['colors']['success']
    )
    await ctx.edit_initial_response(embed=embed)

    is_crisis_active = False


@tanjun.annotations.with_annotated_args(follow_wrapped=True)
@crisis_msg_group.as_sub_command("add")
@crisis_slash_group.as_sub_command("add", "Adds a channel to an ongoing crisis")
async def crisis_add(ctx: tanjun.abc.Context,
                     channel: Annotated[tanjun.annotations.Channel, "The channel to add to the ongoing crisis"]):
    if not is_crisis_active:
        embed = hikari.Embed(
            title='Error',
            description='No ongoing crisis',
            color=config['colors']['error']
        )
        await ctx.respond(embed=embed)
        return

    if is_crisis_loading:
        embed = hikari.Embed(
            title='Error',
            description='A crisis is initializing. Please wait',
            color=config['colors']['error']
        )
        await ctx.respond(embed=embed)
        return

    everyone_role = ctx.get_guild().get_role(config['crisis']['everyone_role_id'])

    full_channel = ctx.get_guild().get_channel(channel.id)
    channel_name = full_channel.name
    overwrites = full_channel.permission_overwrites

    if full_channel.parent_id is None:
        embed = hikari.Embed(
            title='Error',
            description='Channel is a category. Not implemented yet.',
            color=config['colors']['error']
        )
        await ctx.respond(embed=embed)
        return

    if everyone_role.id not in overwrites.keys():
        embed = hikari.Embed(
            title='Error',
            description='Channel securing failed. Please secure manually',
            color=config['colors']['error']
        )
        await ctx.respond(embed=embed)
        return

    everyone_overwrites = overwrites.get(everyone_role.id)
    everyone_overwrites.allow = everyone_overwrites.allow & ~hikari.Permissions.VIEW_CHANNEL
    everyone_overwrites.deny = everyone_overwrites.deny | hikari.Permissions.VIEW_CHANNEL

    if not channel_name.endswith('-☆'):  # add asterisk if not present already
        channel_name += '-☆'

    await full_channel.edit(name=channel_name, permission_overwrites=overwrites.values())

    if channel.id not in TICKET_CHANNEL_CHANGES.keys():
        TICKET_CHANNEL_CHANGES[channel.id] = []

    TICKET_CHANNEL_CHANGES[channel.id].append(config['crisis']['everyone_role_id'])

    if channel.id not in locked_channels:
        locked_channels.append(channel.id)

    embed = hikari.Embed(
        title='Success',
        description=f'{channel.mention} has been secured',
        color=config['colors']['success']
    )
    await ctx.respond(embed=embed)


@crisis_msg_group.as_sub_group("list")
async def crisis_list(_):
    pass


@crisis_list.as_sub_command("changes")
@crisis_list_slash_group.as_sub_command("changes", "Lists channel changes made in the ongoing crisis")
async def crisis_list_changes(ctx: tanjun.abc.Context):
    channels_string = 'Channels affected: \n'

    if not is_crisis_active:
        channels_string = 'No active crisis'
    elif len(locked_channels) < 1:
        channels_string = 'No channels affected'
    else:
        for index, _id in enumerate(locked_channels):
            if (index % 3) == 0:
                channels_string += '\n'
            else:
                channels_string += ' | '
            channels_string += f'<#{_id}>'

    embed = hikari.Embed(
        title='Crisis',
        description=channels_string,
        color=config['colors']['primary']
    )

    await ctx.respond(embed=embed)


@crisis_list.as_sub_command("errors")
@crisis_list_slash_group.as_sub_command("errors", "Lists errors raised during the crisis initialization")
async def crisis_list_errors(ctx: tanjun.abc.Context):
    errors_string = 'Errors:\n'

    if len(errors) < 1:
        errors_string = 'No errors occurred'
    else:
        for error in errors:
            errors_string += f'- *<#{error[1]}>/<@{error[1]}>*: **{error[0]}**\n'

    embed = hikari.Embed(
        title='Crisis',
        description=errors_string,
        color=config['colors']['primary']
    )

    await ctx.respond(embed=embed)


@tanjun.as_loader()
def load(client: tanjun.Client) -> None:
    if not config['modules']['crisis']:
        return

    client.add_component(component)


@tanjun.as_unloader()
def unload(client: tanjun.Client) -> None:
    client.remove_component_by_name(component.name)
