import time
from typing import Annotated

import aiosqlite
import alluka
import hikari
import tanjun

from utils import trigger_typing
from utils.checks.role_checks import mod_check
from utils.config import Config, ConfigHandler
from utils.converters import PlayerInfo, to_player_info
from utils.database import BannedMemberInfo, DBConnection, convert_to_banned

################
#   Commands   #
################

component = tanjun.Component()

bl_slash_group_perms = tanjun.slash_command_group("banlist", "Commands related to our ban list", default_member_permissions=hikari.Permissions.BAN_MEMBERS)
bl_slash_group = tanjun.slash_command_group("banlist", "Commands related to our ban list")

component.with_command(bl_slash_group)


@component.with_message_command
@tanjun.as_message_command_group('banlist', 'bl')
async def bl_msg_group(_):
    pass


@bl_msg_group.as_sub_command("help")
async def help(ctx: tanjun.abc.MessageContext, config: Config = alluka.inject(type=Config)):
    help_embed = hikari.Embed(
        title='Command help',
        color=config['colors']['primary']
    )

    help_embed.add_field(name='Check if a user if banned', value='`+banlist check <IGN>`')
    help_embed.add_field(name='List all info related to the ban of the user',
                         value='`+banlist info <IGN>`\n*__Moderator__ command.*', inline=False)
    help_embed.add_field(name='Command aliases list', value='`+banlist aliases`', inline=False)
    await ctx.respond(embed=help_embed)


@tanjun.with_concurrency_limit("database_commands", follow_wrapped=True)
@tanjun.annotations.with_annotated_args(follow_wrapped=True)
@tanjun.with_check(mod_check, follow_wrapped=True)
# prefix options
@tanjun.with_argument('player_info', converters=to_player_info)
@bl_msg_group.as_sub_command("add", "a")
# slash options
@tanjun.with_str_slash_option("banned_ign", "User's IGN", key='player_info', converters=to_player_info)
@bl_slash_group_perms.as_sub_command("add", "Adds a user to the ban list")
async def add(ctx: tanjun.abc.Context,
              player_info: PlayerInfo,
              reason: Annotated[tanjun.annotations.Str, "Ban reason"],
              config: Config = alluka.inject(type=Config),
              db: aiosqlite.Connection = alluka.inject(type=aiosqlite.Connection)):
    await trigger_typing(ctx)

    cursor: aiosqlite.Cursor = await db.cursor()

    # Check if user is already banned
    await cursor.execute('''
        SELECT *
        FROM "BANNED"
        WHERE uuid=:uuid
    ''', {
        "uuid": player_info['uuid']
    })

    if await cursor.fetchone() is not None:
        embed = hikari.Embed(
            title='Operation Canceled',
            description='User is already banned',
            color=config['colors']['secondary']
        )
        await ctx.respond(embed=embed)
        return

    banned_embed = hikari.Embed(
        title='Banned Member',
        description='',
        color=config['colors']['secondary']
    )

    banned_embed.set_footer(text='SBU Banned List')
    banned_embed.add_field(name='User IGN', value=f"`{player_info['ign']}`", inline=False)
    banned_embed.add_field(name='Reason', value=reason, inline=False)
    banned_embed.add_field(name='UUID Converter', value=f"https://mcuuid.net/?q={player_info['uuid']}", inline=False)

    msg = await ctx.get_guild() \
        .get_channel(config['banlist']['channel_id']) \
        .send(embed=banned_embed)

    response_embed = hikari.Embed(
        title='Success',
        description=f"User `{player_info['ign']}` added to <#{config['banlist']['channel_id']}>",
        color=config['colors']['success']
    )

    # Save banned member to database
    await cursor.execute('''
        INSERT INTO "BANNED"
        VALUES (:uuid, :reason, :moderator, :created_at, :message)
    ''', {
        "uuid": player_info['uuid'],
        "reason": reason,
        "moderator": ctx.author.id,
        "created_at": int(time.time()),
        "message": msg.id
    })

    await ctx.respond(embed=response_embed)
    await cursor.close()
    await db.commit()


@tanjun.with_concurrency_limit("database_commands", follow_wrapped=True)
@tanjun.with_argument('player_info', converters=to_player_info)
@bl_msg_group.as_sub_command("check", "c")
@tanjun.with_str_slash_option("ign", "User's IGN", key='player_info', converters=to_player_info)
@bl_slash_group.as_sub_command("check", "Check whether a user is in our ban list")
async def check(ctx: tanjun.abc.Context, player_info: PlayerInfo,
                config: Config = alluka.inject(type=Config)):
    await trigger_typing(ctx)

    banned = await fetch_user_from_db(player_info['uuid'])

    embed: hikari.Embed

    if banned is None:
        embed = hikari.Embed(
            title='Clear',
            description='User is not present in our banned list',
            color=config['colors']['success']
        )
    else:
        mod = ctx.get_guild().get_member(banned['moderator'])
        if mod is None:
            mod = await ctx.rest.fetch_user(banned['moderator'])

        embed = hikari.Embed(
            title='Not clear',
            description='User is present in our banned list',
            color=config['colors']['error']
        )
        embed.add_field(name='Reason', value=f'{banned["reason"]}', inline=False)
        embed.set_footer(text=f'Banned by {mod if mod is not None else banned["moderator"]}')

    await ctx.respond(embed=embed)


@tanjun.with_concurrency_limit("database_commands", follow_wrapped=True)
@tanjun.with_check(mod_check, follow_wrapped=True)
@tanjun.with_argument('player_info', converters=to_player_info)
@bl_msg_group.as_sub_command("remove", "r", "rm", "delete", "del")
@tanjun.with_str_slash_option("banned_ign", "User's IGN", key='player_info', converters=to_player_info)
@bl_slash_group_perms.as_sub_command("remove", "Remove a user from our ban list")
async def remove(ctx: tanjun.abc.Context, player_info: PlayerInfo,
                 config: Config = alluka.inject(type=Config),
                 db: aiosqlite.Connection = alluka.inject(type=aiosqlite.Connection)):
    await trigger_typing(ctx)

    banned = await fetch_user_from_db(player_info['uuid'])

    if banned is None:
        embed = hikari.Embed(
            title='Error',
            description='User is not present in our database',
            color=config['colors']['error']
        )
        await ctx.respond(embed=embed)
        return

    msg_id = banned['message']
    try:
        channel = ctx.get_guild().get_channel(config['banlist']['channel_id'])
        if isinstance(channel, hikari.TextableChannel):
            await channel.delete_messages(msg_id)

    except hikari.BulkDeleteError:
        pass

    await db.execute('''
        DELETE
        FROM "BANNED"
        WHERE uuid=:uuid
    ''', {
        "uuid": player_info['uuid']
    })

    embed = hikari.Embed(
        title='Success',
        description=f"User `{player_info['ign']}` was removed from <#{config['banlist']['channel_id']}>",
        color=config['colors']['success']
    )

    await ctx.respond(embed=embed)
    await db.commit()


@tanjun.with_concurrency_limit("database_commands", follow_wrapped=True)
@tanjun.annotations.with_annotated_args(follow_wrapped=True)
@tanjun.with_argument('player_info', converters=to_player_info)
@bl_msg_group.as_sub_command("info", "i")
@tanjun.with_str_slash_option("banned_ign", "User's IGN", key='player_info', converters=to_player_info)
@bl_slash_group.as_sub_command("info", "List information regarding a person's ban")
async def info(ctx: tanjun.abc.Context, player_info: PlayerInfo,
               config: Config = alluka.inject(type=Config)):
    await trigger_typing(ctx)

    banned = await fetch_user_from_db(player_info['uuid'])

    if banned is None:
        embed = hikari.Embed(
            title='Error',
            description='User is not present in our database',
            color=config['colors']['error']
        )
        await ctx.respond(embed=embed)
        return

    embed = hikari.Embed(
        title='Banned User Info',
        color=config['colors']['primary']
    )

    mod = ctx.get_guild().get_member(banned['moderator'])
    if mod is None:
        mod = await ctx.rest.fetch_user(banned['moderator'])

    embed.add_field(name='IGN', value=player_info['ign'], inline=False)
    embed.add_field(name='UUID', value=player_info['uuid'], inline=False)
    embed.add_field(name='Banned by', value=f'{mod if mod is not None else banned["moderator"]}', inline=False)
    embed.add_field(name='Reason', value=banned['reason'], inline=False)
    embed.add_field(name='Ban Date', value=f'<t:{banned["banned_at"]}>', inline=False)

    await ctx.respond(embed=embed)


async def fetch_user_from_db(uuid: str) -> BannedMemberInfo | None:
    cursor: aiosqlite.Cursor = await DBConnection().get_db().cursor()

    await cursor.execute('''
        SELECT *
        FROM "BANNED"
        WHERE uuid=:uuid
    ''', {
        "uuid": uuid
    })
    res = await cursor.fetchone()
    await cursor.close()

    if res is None:
        return None

    return convert_to_banned(res)


@tanjun.as_loader()
def load(client: tanjun.Client) -> None:
    if not ConfigHandler().get_config()['modules']['banlist']:
        return

    client.add_component(component)


@tanjun.as_unloader()
def unload(client: tanjun.Client) -> None:
    client.remove_component_by_name(component.name)
