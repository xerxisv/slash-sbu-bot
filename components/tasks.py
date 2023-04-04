import datetime
import os
import tarfile

import aiohttp
import alluka
import hikari.api.cache
import tanjun

from utils.config import Config
from utils.error_utils import exception_to_string

api_key = os.getenv('APIKEY')

component = tanjun.Component()


@component.with_schedule
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


@component.with_schedule
@tanjun.as_interval(datetime.timedelta(days=1))
async def backup_db():
    with tarfile.open("./backup/backup.tar.gz", "w:gz") as tar_handle:
        for root, dirs, files in os.walk("./data"):
            for file in files:
                if file.endswith((".db", ".json")):
                    tar_handle.add(os.path.join(root, file), arcname=file)


@tanjun.as_loader()
def load(client: tanjun.Client):
    client.add_component(component)


@tanjun.as_unloader()
def unload(client: tanjun.Client):
    client.remove_component_by_name(component.name)
