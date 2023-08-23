import datetime
import os
import tarfile
import time

import aiohttp
import aiosqlite
import alluka
import hikari.api.cache
import tanjun
from aiosqlite import Connection

from utils.config import Config, ConfigHandler
from utils.database import DBConnection, convert_to_user
from utils.error_utils import exception_to_string

api_key = os.getenv('APIKEY')

component = tanjun.Component()


@tanjun.as_interval(datetime.timedelta(hours=1))
async def update_member_count(cache: hikari.api.Cache = alluka.inject(type=hikari.api.Cache),
                              config: Config = alluka.inject(type=Config)):
    total_members = 0  # Stores the member count of all the guilds combined
    for idx, guild in enumerate(config['guilds'].keys()):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"https://api.hypixel.net/guild?key={api_key}&id="
                                       f"{config['guilds'][guild]['guild_uuid']}") as resp:
                    assert resp.status == 200  # Unless a guild gets deleted this will never raise

                    guild_info = (await resp.json())["guild"]

        except AssertionError:

            await cache.get_available_guild(config['server_id']).get_channel(config['bot_log_channel_id']) \
                .send(f"Guild info fetch with id `{config['guilds'][guild]['guild_uuid']}` "
                      "did not return a 200.")

        except Exception as exception:
            await cache.get_guild(config['server_id']).get_channel(config['bot_log_channel_id']) \
                .send(exception_to_string('update_member task', exception))

        else:
            new_name = f'{guild_info["name"]}: {str(len(guild_info["members"]))}'
            total_members += int(len(guild_info["members"]))
            vc = cache.get_guild(config['server_id']).get_channel(
                config['guilds'][guild]['member_count_channel_id'])

            if vc is None:
                await cache.get_guild(config['server_id']).get_channel(config['bot_log_channel_id']) \
                    .send(f"Could not fetch channel with id {config['guilds'][guild]['member_count_channel_id']}")

                return

            await vc.edit(name=new_name)

    total_member_vc = cache.get_guild(config['server_id']).get_channel(
        config['tasks']['total_members_channel_id'])
    new_name = "Guild members: " + str(total_members)

    if total_member_vc is None:
        await cache.get_guild(config['server_id']) \
            .get_channel(config['bot_log_channel_id']) \
            .send(f"Could not fetch channel with id {config['tasks']['total_members_channel_id']}")

        return

    await total_member_vc.edit(name=new_name)


@tanjun.as_interval(datetime.timedelta(days=1))
async def backup_db():
    with tarfile.open("./backup/backup.tar.gz", "w:gz") as tar_handle:
        for root, dirs, files in os.walk("./data"):
            for file in files:
                if file.endswith(".gitignore"):
                    continue

                tar_handle.add(os.path.join(root, file), arcname=file)


@tanjun.as_interval(datetime.timedelta(days=1))
async def check_verified(db: aiosqlite.Connection = alluka.inject(type=aiosqlite.Connection),
                         cache: hikari.api.Cache = alluka.inject(type=hikari.api.Cache),
                         config: Config = alluka.inject(type=Config)
                         ):
    cursor: aiosqlite.Cursor = await DBConnection().get_db().cursor()

    uuids = ()

    for idx, guild in enumerate(config['guilds'].keys()):

        guild_uuid = config['guilds'][guild]["guild_uuid"]

        try:
            # fetch guild members
            async with aiohttp.ClientSession() as session:
                res = await session.get(f"https://api.hypixel.net/guild?id={guild_uuid}&key={api_key}")

                assert res.status == 200

                data = await res.json()
                guild_members = data["guild"]["members"]

        except AssertionError:
            await cache.get_guild(config['server_id']) \
                .get_channel(config['bot_log_channel_id']) \
                .send(f"Guild info fetch with id `{config['guilds'][guild]['guild_uuid']}` "
                      "did not return a 200.")
            continue

        except Exception as exception:
            await cache.get_guild(config['server_id']) \
                .get_channel(config['bot_log_channel_id']) \
                .send(exception_to_string('check_verified task', exception))
            continue

        await cursor.execute(f'''
            SELECT *
            FROM "USERS"
            WHERE guild_uuid=:guild_uuid
        ''', {
            "guild_uuid": guild_uuid
        })

        members = await cursor.fetchall()

        for member in members:
            member = convert_to_user(member)

            if any(g_member['uuid'] == member['uuid'] for g_member in guild_members):
                continue

            discord_member = cache.get_guild(config['server_id']).get_member(member['discord_id'])

            if not discord_member:
                continue

            for role in config['verify']['guild_member_roles']:
                role = cache.get_guild(config["server_id"]) \
                    .get_role(role)
                await discord_member.remove_role(role)

            role = cache.get_guild(config["server_id"]) \
                .get_role(config['verify']['member_role_id'])
            await discord_member.remove_role(role)
            uuids = uuids + (f"'{member['uuid']}'",)

    await cursor.execute(f'''
        UPDATE "USERS"
        SET "guild_uuid"=NULL
        WHERE "uuid" IN ({', '.join(uuid for uuid in uuids)})
        ''')

    await cursor.close()
    await db.commit()


@tanjun.as_interval(datetime.timedelta(hours=12))
async def inactives_check(db: aiosqlite.Connection = alluka.inject(type=aiosqlite.Connection),
                          cache: hikari.api.Cache = alluka.inject(type=hikari.api.Cache),
                          config: Config = alluka.inject(type=Config)):
    try:
        await db.execute(f'''
            UPDATE "USERS"
            SET inactive_until=null
            WHERE inactive_until<{int(time.time())}
        ''')
        await db.commit()
    except Exception as exception:
        await cache.get_guild(config["server_id"]) \
            .get_channel(config['bot_log_channel_id']) \
            .send(exception_to_string('inactives_check task', exception))


@tanjun.as_time_schedule(timezone=datetime.timezone.utc, weekly=True, days=6)
async def clear_tatsu(db: Connection = tanjun.inject()):
    await db.execute('''
        UPDATE "USERS"
        SET last_week_tatsu = tatsu_score
    ''')
    await db.commit()

@tanjun.as_loader()
def load(client: tanjun.Client):
    config = ConfigHandler().get_config()

    if config['tasks']['activated']['gtatsu']:
        component.add_schedule(clear_tatsu)
    if config['tasks']['activated']['backup_db']:
        component.add_schedule(backup_db)
    if config['tasks']['activated']['update_member_count']:
        component.add_schedule(update_member_count)
    if config['tasks']['activated']['check_verified']:
        component.add_schedule(check_verified)
    if config['tasks']['activated']['inactives_check']:
        component.add_schedule(inactives_check)

    client.add_component(component)


@tanjun.as_unloader()
def unload(client: tanjun.Client):
    client.remove_component_by_name(component.name)
