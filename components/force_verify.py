import os
import time
from typing import Annotated

import aiosqlite
import alluka
import hikari
import tanjun

from utils import get, trigger_typing
from utils.checks.role_checks import helper_check
from utils.config import Config
from utils.error_utils import log_error

##############
#   Config   #
##############

key = os.getenv('APIKEY')

#############
#  Command  #
#############

component = tanjun.Component()


@component.with_command(follow_wrapped=True)
@tanjun.with_check(helper_check, follow_wrapped=True)
@tanjun.with_cooldown("api_commands", follow_wrapped=True)
@tanjun.with_concurrency_limit("database_commands", follow_wrapped=True)
@tanjun.annotations.with_annotated_args(follow_wrapped=True)
@tanjun.as_message_command('forceverify')
@tanjun.as_slash_command('forceverify', 'Command to force link a discord account')
async def forceverify(ctx: tanjun.abc.Context, ign: Annotated[tanjun.annotations.Str, "The IGN"],
                 account: Annotated[tanjun.annotations.Member, "The member"],
                 config: Config = alluka.inject(type=Config),
                 db: aiosqlite.Connection = alluka.inject(type=aiosqlite.Connection)):
    await trigger_typing(ctx)

    error_embed = hikari.Embed(
        title=f'Error',
        description='Something went wrong. Please try again later',
        color=config['colors']['error']
    )

    # Get user uuid & case sensitive ign
    try:
        # Convert IGN to UUID
        response = await get(f'https://api.mojang.com/users/profiles/minecraft/{ign}')

        assert response.status != 204  # Only returns 204 when the name inputted is wrong

        uuid = (await response.json())['id']
        ign = (await response.json())["name"]
    except AssertionError:  # In case of a 204
        embed = hikari.Embed(
            title=f'Error',
            description='Error fetching information from the API. Recheck the spelling of your IGN',
            color=config['colors']['error']
        )
        await ctx.respond(embed=embed)
        return
    except Exception as exception:  # In case of anything else
        await log_error(ctx, exception)

        await ctx.respond(embed=error_embed)
        return

    # Remove all member roles
    roles = [role for role in list(account.role_ids) if
             role not in config['verify']['guild_member_roles'] and role != config['verify']['member_role_id']]

    await account.edit(roles=roles, reason='Verification Process')

    # Get player hypixel info and guild
    try:
        # Fetch player data
        response = await get(f'https://api.hypixel.net/player?key={key}&uuid={uuid}')
        assert response.status == 200, 'api.hypixel.net/player did not return a 200'
        player = (await response.json())['player']

        # Fetch guild data
        response = await get(f'https://api.hypixel.net/guild?key={key}&player={uuid}')
        assert response.status == 200, 'api.hypixel.net/guild did not return a 200'
        guild = (await response.json())['guild']

    except Exception as exception:  # Log any errors that might araise
        await log_error(ctx, exception)

        await ctx.respond(embed=error_embed)
        return

    # Check player's socials
    try:
        if player['socialMedia']['links']['DISCORD'] != str(ctx.author):
            embed = hikari.Embed(
                title=f'Error',
                description='The discord linked with your hypixel account is not the same as the one you are '
                            'trying to verify with. '
                            '\n You can connect your discord following https://youtu.be/6ZXaZ-chzWI',
                color=config['colors']['error']
            )
            await ctx.respond(embed=embed)
            return
    except KeyError:
        embed = hikari.Embed(
            title=f'Error',
            description='You haven\'t linked your discord with your hypixel account yet\n'
                        'You can connect your discord following https://youtu.be/6ZXaZ-chzWI',
            color=config['colors']['error']
        )
        await ctx.respond(embed=embed)
        return
    except Exception as exception:
        await log_error(ctx, exception)

        await ctx.respond(embed=error_embed)
        return

    roles = list(account.role_ids)

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

    roles = list(dict.fromkeys(roles))

    await account.edit(roles=roles, reason='Verification Process')

    await db.execute('''
        INSERT OR REPLACE INTO "USERS"(uuid, discord_id, ign, guild_uuid, created_at) 
        VALUES (:uuid, :discord_id, :ign, :guild_uuid, :created_at)
    ''', {
        "uuid": uuid,
        "discord_id": account.id,
        "ign": ign,
        "guild_uuid": guild["_id"] if guild else None,
        "created_at": int(time.time())
    })

    await db.commit()

    try:
        await account.edit(nickname=player["displayname"])

    except hikari.ForbiddenError:
        pass

    await ctx.respond(embed=embed)


@tanjun.as_loader()
def load(client: tanjun.Client):
    client.add_component(component)


@tanjun.as_unloader()
def unload(client: tanjun.Client):
    client.remove_component(component)
