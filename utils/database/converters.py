from typing import TypedDict
from aiosqlite import Row


# Banlist
class BannedMemberInfo(TypedDict):
    uuid: str
    reason: str
    moderator: int
    banned_at: int


def convert_to_banned(query_res: Row) -> BannedMemberInfo:
    return {
        "uuid": query_res[0],
        "reason": query_res[1],
        "moderator": query_res[2],
        "banned_at": query_res[3]
    }


# Rep
class RepCommandInfo(TypedDict):
    rep_id: int
    receiver: int
    provider: int
    comments: str
    created_at: float
    msg_id: int


def convert_to_rep(query_res: Row) -> RepCommandInfo:
    return {
        "rep_id": query_res[0],
        "receiver": query_res[1],
        "provider": query_res[2],
        "comments": query_res[3],
        "created_at": query_res[4],
        "msg_id": query_res[5],
    }


# Suggestion
class SuggestionInfo(TypedDict):
    suggestion_number: int
    message_id: int
    author_id: int
    suggestion: str
    answered: bool
    approved: bool
    reason: str
    approved_by: int
    created_at: int
    thread_id: int


def convert_to_suggestion(query_res: Row) -> SuggestionInfo:
    return {
        "suggestion_number": query_res[0],
        "message_id": query_res[1],
        "author_id": query_res[2],
        "suggestion": query_res[3],
        "answered": query_res[4],
        "approved": query_res[5],
        "reason": query_res[6],
        "approved_by": query_res[7],
        "created_at": query_res[8],
        "thread_id": query_res[9]
    }


# User
class UserInfo(TypedDict):
    discord_id: int
    uuid: str
    guild_uuid: str
    ign: str
    inactive_until: int
    tatsu_score: int
    last_week_tatsu: int
    this_week_tatsu_score: int
    gtatsu: int
    created_at: int


def convert_to_user(query_res: Row) -> UserInfo:
    return {
        'uuid': query_res[0],
        'discord_id': query_res[1],
        'ign': (query_res[2]),
        'guild_uuid': query_res[3],
        'inactive_until': query_res[4],
        'tatsu_score': query_res[5],
        'last_week_tatsu': query_res[7],
        'this_week_tatsu_score': query_res[5] - query_res[7],
        'created_at': query_res[6],
        'gtatsu': query_res[8]
    }
