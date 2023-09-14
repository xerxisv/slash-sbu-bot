import os
import time
from typing import Annotated

import aiosqlite
import alluka
import hikari
import tanjun

from utils import get, trigger_typing
from utils.checks.db_checks import registered_check
from utils.config import Config, ConfigHandler
from utils.converters import PlayerInfo, to_player_info
from utils.database import convert_to_user
from utils.error_utils import log_error

##############
#   Config   #
##############

key = os.getenv('APIKEY')

def error_embed(status):
    err_embed = hikari.Embed(
        title=f"Error",
        description="Something went wrong. Please try again later",
        color=ConfigHandler().get_config()['colors']['error']
    )
    err_embed.set_footer(f"Status: `{status}`")
    return err_embed

################
#   Commands   #
################

component = tanjun.Component()


@component.with_command(follow_wrapped=True)
@tanjun.with_cooldown("api_commands", follow_wrapped=True)
@tanjun.with_concurrency_limit("database_commands", follow_wrapped=True)
@tanjun.annotations.with_annotated_args(follow_wrapped=True)
@tanjun.as_message_command('verify')
@tanjun.as_slash_command('verify', 'Links your hypixel account')
async def verify(ctx: tanjun.abc.Context, ign: Annotated[tanjun.annotations.Str, "Your IGN"],
                 config: Config = alluka.inject(type=Config),
                 db: aiosqlite.Connection = alluka.inject(type=aiosqlite.Connection)):
    await trigger_typing(ctx)
    await verification_routine(ctx, ctx.member, ign, config, db)


@component.with_command()
@tanjun.with_cooldown("api_commands")
@tanjun.with_concurrency_limit("database_commands")
@tanjun.annotations.with_annotated_args()
@tanjun.as_slash_command('force-verify', 'Force link a hypixel account', default_to_ephemeral=True,
                         default_member_permissions=hikari.Permissions.MUTE_MEMBERS)
async def force_verify(ctx: tanjun.abc.Context, member: Annotated[tanjun.annotations.Member, "The member"],
                       ign: Annotated[tanjun.annotations.Str, "The IGN"],
                       config: Config = alluka.inject(type=Config),
                       db: aiosqlite.Connection = alluka.inject(type=aiosqlite.Connection)):
    await trigger_typing(ctx)
    await verification_routine(ctx, member, ign, config, db)


@component.with_command(follow_wrapped=True)
@tanjun.with_check(registered_check, follow_wrapped=True)
@tanjun.with_concurrency_limit("database_commands", follow_wrapped=True)
@tanjun.as_message_command('unverify')
@tanjun.as_slash_command('unverify', 'Removes the link to your hypixel account')
async def unverify(ctx: tanjun.abc.Context,
                   config: Config = alluka.inject(type=Config),
                   db: aiosqlite.Connection = alluka.inject(type=aiosqlite.Connection)):
    # Perform a left outer intersection on the current roles and the roles to be removed
    roles = list(ctx.member.role_ids)
    roles_to_remove = [hikari.Snowflake(r) for r in config['verify']['guild_member_roles']] + \
                      [hikari.Snowflake(config['verify']['member_role_id']),
                       hikari.Snowflake(config['verify']['verified_role_id'])]
    roles = list(dict.fromkeys(roles + roles_to_remove))

    for role in roles_to_remove:
        roles.remove(role)

    await ctx.member.edit(roles=roles, reason='Unverify')

    await db.execute('''
        UPDATE "USERS"
        SET discord_id=1, guild_uuid=NULL
        WHERE discord_id=:discord_id
    ''', {
        "discord_id": ctx.member.id
    })
    await db.commit()

    embed = hikari.Embed(
        title=f'Verification',
        description=f'You have been unverified.',
        color=config['colors']['secondary']
    )
    await ctx.respond(embed=embed)


@component.with_command(follow_wrapped=True)
@tanjun.with_str_slash_option('ign', 'The user\'s IGN', key='player_info', default=None, converters=to_player_info)
@tanjun.with_user_slash_option('user', 'The user', default=None)
@tanjun.as_slash_command('user_info', 'Returns the info of the given user stored in the database',
                         default_member_permissions=hikari.Permissions.MUTE_MEMBERS)
async def user_info(ctx: tanjun.abc.Context, user: hikari.User, player_info: PlayerInfo,
                    config: Config = alluka.inject(type=Config),
                    db: aiosqlite.Connection = alluka.inject(type=aiosqlite.Connection)):
    # Make script depending on info passed
    if user is not None:
        script = ('''
            SELECT *
            FROM "USERS"
            WHERE discord_id=:discord_id
        ''', {
            "discord_id": user.id
        })
    elif player_info is not None:
        script = ('''
            SELECT *
            FROM "USERS"
            WHERE uuid=:uuid
        ''', {
            "uuid": player_info['uuid']
        })
    else:
        script = ('''
            SELECT *
            FROM "USERS"
            WHERE discord_id=:discord_id
        ''', {
            "discord_id": ctx.member.id
        })

    cursor: aiosqlite.Cursor
    async with db.cursor() as cursor:
        await cursor.execute(*script)
        res = await cursor.fetchone()

    if not res:
        embed = hikari.Embed(
            title='Error',
            description='User not found',
            color=config['colors']['error']
        )
        await ctx.respond(embed=embed)
        return

    # Put info in the embed
    user = convert_to_user(res)
    embed = hikari.Embed(
        title='User Info',
        color=config['colors']['primary']
    )

    if user['discord_id'] > 1:
        embed.add_field(name="Discord", value=f"<@{user['discord_id']}>")

    if user['ign'] is not None:
        embed.add_field(name="Last known IGN", value=f"`{user['ign']}`")

    if user['guild_uuid']:
        res = await get(f"https://api.slothpixel.me/api/guilds/id/{user['guild_uuid']}")
        if res.status != 200:
            await ctx.respond(embed=error_embed(res.status))
            return

        data = await res.json()
        if data['guild']:
            embed.add_field(name="Guild", value=data['name'])

    if user['inactive_until']:
        embed.add_field(name="Inactive until", value=f"<t:{user['inactive_until']}:d>")

    embed.add_field(name="Verified at", value=f"<t:{user['created_at']}:d>")

    await ctx.respond(embed=embed)


async def verification_routine(ctx: tanjun.abc.Context, member: hikari.Member, ign: str,
                               config: Config, db: aiosqlite.Connection):


    # Get user uuid & case sensitive ign
    res = None
    try:
        # Convert IGN to UUID
        res = await get(f'https://api.mojang.com/users/profiles/minecraft/{ign}')

        assert res.status != 204  # Only returns 204 when the name inputted is wrong

        uuid = (await res.json())['id']
        ign = (await res.json())["name"]
    except AssertionError:  # In case of a 204
        embed = hikari.Embed(
            title=f"Error",
            description="Error fetching information from the API. Recheck the spelling of your IGN",
            color=config['colors']['error']
        )
        embed.set_footer(f"Status: `{res.status}`")
        await ctx.respond(embed=embed)
        return
    except Exception as exception:  # In case of anything else
        await log_error(ctx, exception)

        await ctx.respond(embed=error_embed(res.status))
        return

    await db.execute('''
            INSERT OR REPLACE INTO "USERS"(uuid, discord_id, ign, guild_uuid, created_at) 
            VALUES (:uuid, :discord_id, :ign, :guild_uuid, :created_at)
        ''', {
        "uuid": uuid,
        "discord_id": member.id,
        "ign": ign,
        "guild_uuid": guild["_id"] if guild else None,
        "created_at": int(time.time())
    })

    await db.commit()
    await update_routine(ctx, member, config, db, uuid)

    

async def update_routine(ctx: tanjun.abc.Context, member: hikari.Member,
                               config: Config, db: aiosqlite.Connection, uuid: str):
    embed = None
    roles = [role for role in list(member.role_ids) if
             role not in config['verify']['guild_member_roles'] and role != config['verify']['member_role_id']]

    await member.edit(roles=roles, reason="Verification Process")
    
    try:
        # Fetch player data
        res = await get(f"https://api.hypixel.net/player?key={key}&uuid={uuid}")
        assert res.status == 200, 'api.hypixel.net/player did not return a 200'
        player = (await res.json())['player']

        # Fetch guild data
        res = await get(f'https://api.hypixel.net/guild?key={key}&player={uuid}')
        assert res.status == 200, "api.hypixel.net/guild did not return a 200"
        guild = (await res.json())['guild']

    except Exception as exception:  # Log any errors that might araise
        await log_error(ctx, exception)

        await ctx.respond(embed=error_embed(res))
        return False

    # Check player's socials
    try:
        if player['socialMedia']['links']['DISCORD'] != str(member):
            embed = hikari.Embed(
                title="Error",
                description="The discord linked with your hypixel account is not the same as the one you are "
                            "trying to verify with.\n"
                            f"Your tag: `{str(member)}`\n"
                            f"Linked tag: `{player['socialMedia']['links']['DISCORD']}`\n"
                            "You can connect your discord following https://youtu.be/6ZXaZ-chzWI",
                color=config['colors']['error']
            )
            await ctx.respond(embed=embed)
            return False
    except KeyError:
        embed = hikari.Embed(
            title="Error",
            description="You haven't linked your discord with your hypixel account yet\n"
                        "You can connect your discord following https://youtu.be/6ZXaZ-chzWI",
            color=config['colors']['error']
        )
        await ctx.respond(embed=embed)
        return False
    except TypeError:
        embed = hikari.Embed(
            title="Error",
            description="Player does not have a hypixel account.",
            color=config['colors']['error']
        )
        await ctx.respond(embed=embed)
        return
    except Exception as exception:
        await log_error(ctx, exception)

        await ctx.respond(embed=error_embed(''))
        return False

    if guild is None or guild["name"].upper() not in config['guilds'].keys():
        embed = hikari.Embed(
            title=f'Verification',
            description='You are not in any of the SBU guilds. You are now verified without '
                        'the guild member roles.',
            color=config['colors']['secondary']
        )

    else:
        roles += [hikari.Snowflake(config['guilds'][guild["name"].upper()]['member_role_id']),
                  hikari.Snowflake(config['verify']['member_role_id'])]

        embed = hikari.Embed(
            title=f'Verification',
            description=f'You have been verified as a member of {guild["name"]}',
            color=config['colors']['primary']
        )

    roles.append(hikari.Snowflake(config['verify']['verified_role_id']))

    roles = set(roles)

    try:
        await member.edit(roles=roles, reason='Verification Process')
    except hikari.BadRequestError:
        embed = hikari.Embed(
            title="Error",
            description="Something went wrong. Please try again later.",
            color=config['colors']['error']
        )
        await ctx.respond(embed=embed)
        return False
    
    try:
        await member.edit(nickname=player["displayname"])
    except hikari.ForbiddenError:
        pass
    
    await ctx.respond(embed=embed)
    return True



@tanjun.as_loader()
def load(client: tanjun.Client):
    client.add_component(component)


@tanjun.as_unloader()
def unload(client: tanjun.Client):
    client.remove_component(component)