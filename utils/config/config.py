import json
from typing import TypedDict

from utils import Singleton

import aiofiles


class BanList(TypedDict):
    channel_id: int


class Colors(TypedDict):
    success: int
    error: int
    primary: int | None
    secondary: int | None


class Crisis(TypedDict):
    ignored_categories: list[int]
    ignored_roles: list[int]
    ticket_channels: list[int]
    everyone_role_id: int


class Files(TypedDict):
    allowed_category: int


class GuildInfo(TypedDict):
    member_role_id: int
    guild_uuid: str
    bridge_uuid: str
    member_count_channel_id: int


class GTatsu(TypedDict):
    bridge_bot_ids: list[int]
    bridge_channel_ids: list[int]
    top_active_role_id: int


class HelperAcademy(TypedDict):
    ticket_commands_channel_id: int


class Requirements(TypedDict):
    weight: int
    dungeon_lvl: int
    slayer_xp: int

class Masters(TypedDict):
    main: Requirements
    jr: Requirements


class Misc(TypedDict):
    allowed_role_id: int


class Moderation(TypedDict):
    action_log_channel_id: int
    appeals_invite: str


class Rep(TypedDict):
    rep_log_channel_id: int


class WeightRoleInfo(TypedDict):
    role_id: int
    weight_req: int
    name: str
    previous: list[int]


class Stats(TypedDict):
    weight_banned_role_id: int
    default_weight_role_id: int
    weight_roles: dict[str, WeightRoleInfo]


class Suggestions(TypedDict):
    suggestions_channel_id: int


class ActivatedTasks(TypedDict):
    update_member_count: bool
    backup_db: bool
    inactives_check: bool
    check_verified: bool


class Tasks(TypedDict):
    activated: ActivatedTasks
    total_members_channel_id: int
    booster_role_id: int
    booster_log_channel_id: int


class Qotd(TypedDict):
    qotd_channel_id: int
    qotd_role_id: int


class Verify(TypedDict):
    member_role_id: int
    guild_member_roles: list[int]
    verified_role_id: int


class Info(TypedDict):
    info_channel_id: int


class Config(TypedDict, total=False):
    logo_url: str | None
    server_id: int

    jr_mod_role_id: int
    mod_role_id: int
    admin_role_id: int
    jr_admin_role_id: int
    co_owner_role_id: int
    owner_role_id: int

    mod_chat_channel_id: int
    admin_chat_channel_id: int
    bot_log_channel_id: int

    guilds: dict[str, GuildInfo]
    colors: Colors
    modules: dict[str, bool]
    banlist: BanList
    crisis: Crisis
    files: Files
    gtatsu: GTatsu
    helper_academy: HelperAcademy
    masters: Masters
    misc: Misc
    moderation: Moderation
    rep: Rep
    stats: Stats
    suggestions: Suggestions
    tasks: Tasks
    qotd: Qotd
    verify: Verify
    info: Info


class ConfigHandler(metaclass=Singleton):
    config_file_path = './config.json'

    def __init__(self):
        self.__config: Config = {}

    def get_config(self) -> Config:
        return self.__config

    async def load_config(self) -> None:
        async with aiofiles.open(self.config_file_path, mode='r') as f:
            self.__config = json.loads(await f.read())

    async def save_config(self) -> None:
        async with aiofiles.open(self.config_file_path, mode='w') as f:
            await f.write(json.dumps(self.__config))

    async def set_val(self, keys: list[str], val):
        data = self.__config
        last_key = keys[-1]

        for k in keys[:-1]:
            data = data[k]
        data[last_key] = val

        await ConfigHandler().save_config()
        await ConfigHandler().load_config()
