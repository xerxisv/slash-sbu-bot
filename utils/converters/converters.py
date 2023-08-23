import typing

import humanfriendly

from utils import extract_uuid
from uuid import UUID

class PlayerInfo(typing.TypedDict):
    ign: str
    uuid: str

def to_timestamp(argument: str) -> int:
    try:
        return int(humanfriendly.parse_timespan(argument))
    except humanfriendly.InvalidTimespan:
        raise ValueError('Invalid time', argument) from humanfriendly.InvalidTimespan

async def to_player_info(argument: str) -> PlayerInfo:
    uuid: str
    if (uuid := await extract_uuid(argument)) is None:
        raise ValueError('Invalid IGN', argument) from NameError

    return {"ign": argument, "uuid": uuid}
