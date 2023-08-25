import time

import aiohttp
import aiosqlite
import hikari
import tanjun

from utils import weighted_randint
from utils.config import Config
from utils.converters import to_player_info
from utils.database import convert_to_user

TATSU_CD = 120
tatsu_dates = {}
last_commit = 0
import os


async def handle_warn(message: hikari.GuildMessageCreateEvent, config: Config):
    if config['jr_mod_role_id'] not in message.member.role_ids:
        return

    # Split the message on every space character
    split_msg = message.content.split(' ')
    # If the message is less than 2 words long then it's an invalid warn command, return
    if len(split_msg) < 3:
        return

    # Else remove the discord formatting characters from the mention
    user_id = split_msg[1].replace('<', '').replace('@', '').replace('>', '')

    # And check if it was indeed a mention
    if not user_id.isnumeric():
        return

    # Fetch the member with the specified ID
    member: hikari.Member = message.get_guild().get_member(int(user_id))

    if member is None:
        member = await message.app.rest.fetch_member(message.get_guild(), int(user_id))

    # Make sure member exists and is not staff
    if member is None or config['jr_mod_role_id'] in member.role_ids:
        return

    await message.get_guild().get_channel(config['moderation']['action_log_channel_id']).send(
        f"Moderator: {message.author.mention} \n"
        f"User: {member.mention} \n"
        f"Action: Warn \n"
        f"Reason: {' '.join(split_msg[2:])}")

    await message.get_channel().send("Log created")


def is_warn(message: str):
    return message and message.startswith("!warn")


def is_bridge_message(message: hikari.Message, config: Config):
    gtatsu_config = config['gtatsu']
    return message.channel_id in gtatsu_config['bridge_channel_ids'] and message.author.id in gtatsu_config[
        'bridge_bot_ids'] and len(message.embeds) > 0 and message.embeds[0].author is not None


def ensure_cooldown(ign: str) -> bool:
    return False if ign not in tatsu_dates else tatsu_dates[ign] + TATSU_CD > int(time.time())


async def handle_tatsu(message: hikari.GuildMessageCreateEvent,
                         db: aiosqlite.Connection = tanjun.inject()):
    ign = message.embeds[0].author.name

    if not isinstance(ign, str):
        return
    if ign.find(' ') > 0:
        return
    if ensure_cooldown(ign):
        return
    player_info = await to_player_info(ign)
    script = ('''
                SELECT *
                FROM "USERS"
                WHERE uuid=:uuid
            ''', {
        "uuid": player_info['uuid']
    })
    cursor: aiosqlite.Cursor
    async with db.cursor() as cursor:
        await cursor.execute(*script)
        res = await cursor.fetchone()

    if not res:
        return

    user = convert_to_user(res)

    if user['discord_id'] < 1:
        return

    tatsu_score = weighted_randint(12, 3)
    session = aiohttp.ClientSession()
    headers = {'Content-Type': 'application/json', 'Authorization': os.getenv("tatsukey")}
    url = f'https://api.tatsu.gg/v1/guilds/764326796736856066/members/{user["discord_id"]}/score'
    json = {'action': 0, 'amount': tatsu_score}

    await session.patch(url, headers=headers, json=json)

    tatsu_dates[ign] = int(time.time())
