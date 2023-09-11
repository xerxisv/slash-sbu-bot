import asyncio
import os
import time
from typing import Annotated

import aiohttp
import aiosqlite
import alluka
import hikari
import miru
import tanjun

from utils import get, trigger_typing
from utils.checks.db_checks import registered_check
from utils.checks.role_checks import jr_mod_check
from utils.config import ConfigHandler
from utils.converters import PlayerInfo, to_player_info, to_timestamp
from utils.database import UserInfo, convert_to_user
from utils.error_utils import log_error

################
#    Config    #
################

config = ConfigHandler().get_config()
api_key = os.getenv("APIKEY")

guild_choices = Annotated[tanjun.annotations.Str, "Guild name", tanjun.annotations.Choices(
    list(map(lambda s: s.lower(), list(config['guilds'].keys()))))]


########################
#    Button Classes    #
########################

class InactiveListButton(miru.Button):
    def __init__(self, player_list: str):
        self.player_list = player_list
        super().__init__(style=hikari.ButtonStyle.PRIMARY, label="Get kick list")

    async def callback(self, ctx: miru.ViewContext) -> None:
        kick_list = ""
        for ign in self.player_list.split('\n')[1:][::-1]:
            kick_list += ign + " "

        file = hikari.Bytes(bytes(kick_list, encoding='utf-8'), 'kick-list.txt')
        await ctx.respond(attachment=file)


class InactiveKickButton(miru.Button):
    def __init__(self, user_id: int, player_list: str, endpoint: str):
        self.user_id = user_id
        self.player_list = player_list
        self.endpoint = endpoint
        super().__init__(style=hikari.ButtonStyle.DANGER, label="Kick bottom 5")

    async def callback(self, ctx: miru.ViewContext) -> None:
        if ctx.user.id != self.user_id:
            return

        view = miru.View(timeout=30)
        view.add_item(InactiveListButton(self.player_list))

        msg = await ctx.edit_response(components=view)
        await view.start(msg)

        await ctx.get_channel().trigger_typing()

        async with aiohttp.ClientSession(trust_env=True) as session:
            # Hack to avoid the blank string :P
            for ign in self.player_list.split('\n')[1:][-1:-6:-1]:
                await session.post(
                    url=self.endpoint + 'kick',
                    headers={'Content-Type': 'application/json'},
                    json={'username': ign, 'reason': 'Inactivity kick. Join back.'}
                )
                await asyncio.sleep(1)

        await ctx.get_channel().send("Successfully kicked 5 guild members")


################
#   Commands   #
################

component = tanjun.Component()

inactive_group = tanjun.SlashCommandGroup("inactive", "Inactivity checks and inactivity list editing")
inactive_force_group = inactive_group.make_sub_group("force", "Force add/remove a player from inactivity list")

inactive_force_group.with_check(jr_mod_check)

component.add_slash_command(inactive_group)


@tanjun.with_cooldown("api_commands")
@tanjun.with_check(jr_mod_check)
@tanjun.annotations.with_annotated_args()
@tanjun.with_concurrency_limit("database_commands")
@inactive_group.as_sub_command("check", "Checks for inactive players in a given guild")
async def inactive_check(ctx: tanjun.abc.SlashContext, guild: guild_choices,
                         db: aiosqlite.Connection = alluka.inject(type=aiosqlite.Connection)):
    await trigger_typing(ctx)

    session = aiohttp.ClientSession()

    cursor: aiosqlite.Cursor
    async with db.cursor() as cursor:
        await cursor.execute('''
            SELECT *
            FROM "USERS"
            WHERE inactive_until IS NOT null
        ''')

        values = await cursor.fetchall()

    inactives_uuids = [inactive[0] for inactive in values]

    res = await session.get(f'https://api.hypixel.net/guild?key={api_key}&name={guild}')

    if res.status != 200:
        embed = hikari.Embed(
            title='Error',
            description='Something went wrong.',
            color=config['colors']['error']
        )
        embed.set_footer(f'Status code: {res.status}')
        await ctx.respond(embed=embed)
        await session.close()
        return

    data = await res.json()

    embed = hikari.Embed(
        title=f"Inactive List for {data['guild']['name']}",
        description=f"Loading, please wait <a:loading:978732444998070304>",
        color=config['colors']['secondary']
    )
    await ctx.respond(embed=embed)

    embed_body = ""  # List of inactive IGNs (or UUIDs if API error)
    total_inactive = 0  # Sum of inactive players

    for player in data["guild"]["members"]:  # for every member in the guild
        # Check if they joined recently. This exists just to skip some unnecessary api calls for new members
        if (time.time() - (player['joined'] / 1000) - 604800) < 0:
            continue
        if player["uuid"] in inactives_uuids:
            continue

        # if total exp is over the minimum or player uuid is in the inactives then go to next member
        if sum(player["expHistory"].values()) > config['min_gexp']:
            continue

        try:  # Fetch player info from hypixel API
            hypixel_res = await session.get(f"https://api.hypixel.net/player?key={api_key}&uuid={player['uuid']}")
            # Ensure OK status
            assert hypixel_res.status == 200, 'Hypixel did not return a 200'

            hypixel_prof = await hypixel_res.json()
            # Ensure player exists
            assert hypixel_prof['player'] is not None, f'Player with UUID {player["uuid"]} not found'

        except Exception as exception:  # If there is an exception, log it and add the uuid in the embed
            await log_error(ctx, exception)
            embed_body += f'\n{player["uuid"]}'

        else:  # Else
            # Continue if player has logged in the last 7 days
            try:
                if (hypixel_prof['player']['lastLogin'] / 1000) + 604800 > time.time():
                    continue
            except KeyError:
                pass
            except Exception as exception:
                await log_error(ctx, exception)
            # Add them to inactives if not
            username = hypixel_prof['player']['displayname']
            embed_body += f"\n{username}"

        total_inactive += 1  # Increment the inactive total

    await session.close()

    embed = hikari.Embed(
        title=f"Inactive List for {data['guild']['name']}",
        description=f"{total_inactive} members were found to be inactive."
                    f"```{embed_body}```",
        color=config['colors']['primary']
    )

    view = miru.View(timeout=30)
    view.add_item(InactiveListButton(embed_body))

    if config['jr_admin_role_id'] in ctx.member.role_ids:
        view.add_item(InactiveKickButton(ctx.member.id, embed_body, config['guilds'][guild.upper()]['endpoint']))

    msg = await ctx.edit_initial_response(embed=embed, components=view)
    await view.start(msg)


@tanjun.with_check(registered_check)
@tanjun.with_concurrency_limit("database_commands")
@tanjun.with_str_slash_option('afk_time', 'Approximate afk time. Ex: 14d -> 14 days', converters=to_timestamp)
@inactive_group.as_sub_command("add", "Adds you to the inactivity list")
async def inactive_add(ctx: tanjun.abc.SlashContext,
                       afk_time: int,
                       db: aiosqlite.Connection = alluka.inject(type=aiosqlite.Connection)):
    if afk_time < 604800 or afk_time > 2592000:
        embed = hikari.Embed(
            title='Error',
            description='Invalid Time. **Min 7 days, max 30**.',
            color=config['colors']['error']
        )
        await ctx.respond(embed=embed)
        return

    afk_time = int(afk_time + time.time())

    await db.execute('''
        UPDATE "USERS"
        SET inactive_until=:afk_time
        WHERE discord_id=:discord_id
    ''', {
        "afk_time": afk_time,
        "discord_id": ctx.author.id
    })
    await db.commit()

    embed = hikari.Embed(
        title=f'Success',
        description=f'You have been added to Inactive list until <t:{afk_time}:D>',
        color=config['colors']['success']
    )

    await ctx.respond(embed=embed)


@tanjun.with_check(jr_mod_check)
@inactive_group.as_sub_command("list", "Lists all the users with an inactivity notice")
async def inactive_list(ctx: tanjun.abc.SlashContext,
                        db: aiosqlite.Connection = alluka.inject(type=aiosqlite.Connection)):
    cursor: aiosqlite.Cursor
    async with db.cursor() as cursor:
        await cursor.execute('''
            SELECT *
            FROM "USERS"
            WHERE inactive_until IS NOT NULL AND discord_id != 0
        ''')
        member_list = await cursor.fetchall()

    embed_body = '**IGN** | **Username** | **Inactive until**\n'

    for row in member_list:
        member: UserInfo = convert_to_user(row)
        mention = f"<@{member['discord_id']}>" if member['discord_id'] != 1 else '-'
        embed_body += f"{member['ign']} | {mention} | " \
                      f"<t:{member['inactive_until']}:D>\n"

    if len(embed_body) > 2000:
        attachment = hikari.Bytes(bytes(embed_body, encoding='utf-8'), 'inactives.txt')

        await ctx.respond(attachment=attachment)
        return

    embed = hikari.Embed(
        title='Inactive List',
        description=embed_body,
        color=config['colors']['primary']
    )

    await ctx.respond(embed=embed)
    pass


@tanjun.with_str_slash_option("afk_time", "Approximate afk time", converters=to_timestamp)
@tanjun.with_str_slash_option("ign", "User's IGN", converters=to_player_info, key='player_info')
@inactive_force_group.as_sub_command("add", "Adds a user to the inactivity list")
async def inactive_force_add(ctx: tanjun.abc.SlashContext,
                             player_info: PlayerInfo,
                             afk_time: int,
                             db: aiosqlite.Connection = alluka.inject(type=aiosqlite.Connection)):
    if afk_time < 604800 or afk_time > 2592000:
        embed = hikari.Embed(
            title='Error',
            description='Invalid Time \nEnter time in days.\n Min 7, max 30. Ex: 10d for 10 days',
            color=config['colors']['error']
        )
        await ctx.respond(embed=embed)
        return

    afk_time = int(afk_time + time.time())

    res = await get(f"https://api.hypixel.net/guild?player={player_info['uuid']}&key={api_key}")
    data = await res.json()

    if res.status != 200 or data['guild'] is None:
        embed = hikari.Embed(
            title='Error',
            description='User either not found, or is not in a guild',
            color=config['colors']['error']
        )
        embed.set_footer(f"Status code: {res.status} | Guild: {data['guild']}")

        await ctx.respond(embed=embed)
        return

    cursor: aiosqlite.Cursor
    async with db.cursor() as cursor:
        # Check if user is registered
        await cursor.execute('''
            SELECT COUNT(1)
            FROM "USERS"
            WHERE uuid=:uuid
        ''', {"uuid": player_info['uuid']})
        count = (await cursor.fetchone())[0]

        if count == 0:  # If they are not then create new entry
            print('a')
            await cursor.execute('''
                INSERT INTO "USERS"(uuid, discord_id, ign, created_at, inactive_until) 
                VALUES (:uuid, :discord_id, :ign, :created_at, :inactive_until) 
            ''', {
                "uuid": player_info['uuid'],
                "discord_id": 1,
                "ign": player_info['ign'],
                "created_at": int(time.time()),
                "inactive_until": afk_time
            })
        else:  # If they are then update the inactive_until field
            await cursor.execute('''
                UPDATE "USERS"
                SET inactive_until=:inactive_until
                WHERE uuid=:uuid
            ''', {
                "uuid": player_info['uuid'],
                "inactive_until": afk_time
            })

    embed = hikari.Embed(
        title='Success',
        description=f"Successfully added {player_info['ign']} to the inactive list until <t:{afk_time}:D>",
        color=config['colors']['success']
    )

    await db.commit()
    await ctx.respond(embed=embed)


@tanjun.with_str_slash_option("ign", "User's IGN", key="player_info", converters=to_player_info)
@inactive_force_group.as_sub_command("remove", "Removes a user from the inactivity list")
async def inactive_force_remove(ctx: tanjun.abc.SlashContext, player_info: PlayerInfo,
                                db: aiosqlite.Connection = alluka.inject(type=aiosqlite.Connection)):
    await db.execute('''
        DELETE
        FROM "USERS"
        WHERE uuid=:uuid
    ''', {"uuid": player_info['uuid']})

    embed = hikari.Embed(
        title='Success',
        description=f"Successfully removed {player_info['ign']} from inactives.",
        color=config['colors']['success']
    )

    await db.commit()
    await ctx.respond(embed=embed)


@tanjun.as_loader()
def load(client: tanjun.Client):
    if not ConfigHandler().get_config()['modules']['inactives']:
        return
    client.add_component(component)


@tanjun.as_unloader()
def unload(client: tanjun.Client):
    client.remove_component_by_name(component.name)
