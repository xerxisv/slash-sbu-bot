import asyncio
import datetime
import re
from contextlib import suppress
from typing import Any, Awaitable, Callable, List, Optional, Sequence

import hikari

from utils.cmd_triggers.cmd_descriptor import EmbedType, FieldType, ParamTypesEnum, ResponseObjectType


def convert_timestamp(stp: str | None) -> datetime.datetime | None:
    if stp is None:
        return None
    # Time format as given from discohook
    return datetime.datetime.fromisoformat(stp).astimezone(datetime.timezone.utc)


def create_embeds(embed_list: Sequence[EmbedType]) -> List[hikari.Embed]:
    embeds = []
    embed_obj: EmbedType
    field: FieldType

    for embed_obj in embed_list:
        embed = hikari.Embed()

        embed.title = embed_obj.get('title')
        embed.description = embed_obj['description']
        embed.url = embed_obj.get('url')
        embed.color = embed_obj.get('color')

        embed.set_image(embed_obj.get('image', {'url': None})['url'])  # Hack to avoid KeyError
        embed.set_thumbnail(embed_obj.get('thumbnail', {'url': None})['url'])

        embed.timestamp = convert_timestamp(embed_obj.get('timestamp')) if embed_obj.get(
            'timestamp') != "now" else datetime.datetime.now(tz=datetime.timezone.utc)

        embed.set_author(
            name=embed_obj.get('author', {'name': None})['name'],
            url=embed_obj.get('author', {'url': None}).get('url'),
            icon=embed_obj.get('author', {'icon_url': None}).get('icon_url')
        )
        embed.set_footer(
            text=embed_obj.get('footer', {'text': None})['text'],
            icon=embed_obj.get('footer', {'icon_url': None}).get('icon_url')
        )

        for field in embed_obj.get('fields', []):
            embed.add_field(name=field['name'], value=field['value'])

        embeds.append(embed)

    return embeds


async def send_res(event: hikari.GuildMessageCreateEvent, res_obj: ResponseObjectType,
                   delete_after: Optional[int]) -> None:
    embeds = create_embeds(res_obj.get('embeds', []))

    msg = await event.message.respond(
        content=res_obj['content'],
        embeds=embeds if embeds else None,
        reply=event.message,
        user_mentions=False,
        role_mentions=False,
        mentions_everyone=False
    )

    if not delete_after:
        return

    await asyncio.sleep(delete_after)

    with suppress(hikari.NotFoundError, hikari.ForbiddenError):
        await msg.delete()


def convert_parameters(params: dict[str, ParamTypesEnum]) -> List[Any]:
    type_conversion_map: dict[ParamTypesEnum, Callable[[str], Any]] = {
        ParamTypesEnum.INT: int,
        ParamTypesEnum.STR: lambda s: s,
        ParamTypesEnum.USER: lambda user: int(user.removeprefix("<@").removesuffix(">")),
        ParamTypesEnum.ROLE: lambda role: int(role.removeprefix("<@&").removesuffix(">"))
    }

    converted_params = []

    for param in params.items():
        converted_params.append(type_conversion_map[param[1]](param[0]))

    return converted_params


def format_res(params: list[str], obj):
    if isinstance(obj, list):
        return [format_res(params, v) for v in obj]
    elif isinstance(obj, dict):
        return {k: format_res(params, v) for k, v in obj.items()}
    elif isinstance(obj, str):
        if re.match("[^\\\]*{[0-9]*}.*", obj) is not None:
            return obj.format(*params)
        return obj


def convert_actions(action_ids: Sequence[int]):
    action_conversion_map: list[Callable[[...], Awaitable[bool]]] = [
        give_role_action, remove_role_action
    ]

    for action_id in action_ids:
        yield action_conversion_map[action_id]


async def give_role_action(event: hikari.GuildMessageCreateEvent, role_id: hikari.Snowflakeish,
                           member_id: hikari.Snowflakeish = None):
    member = event.get_guild().get_member(member_id) if member_id else event.member

    role = member.get_guild().get_role(role_id)
    roles = set(member.get_roles())

    if role and member:
        roles.add(role)
        await member.edit(roles=roles)
        return True

    return False, "Member or role not found"


async def remove_role_action(event: hikari.GuildMessageCreateEvent, role_id: hikari.Snowflakeish,
                             member_id: hikari.Snowflakeish):
    member = event.get_guild().get_member(member_id)
    roles = list(member.role_ids)

    if member and role_id in roles:
        roles.remove(role_id)
        await member.edit(roles=roles)
        return True

    return False, "Member or role not found"

# async def promote_in_game_action(member_id: hikari.Snowflakeish):
#     db = DBConnection().get_db()
#
#     cursor: aiosqlite.Cursor
#     async with db.cursor() as cursor:
#         await cursor.execute('''
#             SELECT ign, guild_uuid
#             FROM USERS
#             WHERE discord_id=:member_id
#         ''', {
#             "member_id": member_id
#         })
#         res = await cursor.fetchone()
#
#     if not res:
#         return False, "Member not found. Maybe they are not verified"
#     if not (guild_uuid:=res[1]):
#         return False, "Member is not part of a guild"
#
#     ign = res[0]
#     guilds = ConfigHandler().get_config()['guilds']
#     endpoint = [guilds[guild]['endpoint'] for guild in guilds if guilds[guild]['guild_uuid'] == guild_uuid][0]
#
#     async with aiohttp.ClientSession() as session:
#         await session.post(
#             url=endpoint + '/promote',
#             data={"username": ign}
#         )
#
#     return True
